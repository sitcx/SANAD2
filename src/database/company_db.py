"""Company side storage: postings, the candidate pool (talents) and applications.

Business rules live here so the API stays thin:
- match = share of the posting's required skills the candidate has (0-100)
- status changes follow ALLOWED (same rules as the web UI)
- indicators are computed from the stored applications, not hard-coded
"""
from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timedelta, timezone

from src.agent.core.config import project_path
from src.database.db import connect
from src.logger import get_logger, log_step

log = get_logger("database.company")
SEED_FILE = "src/data/company_seed.json"

STATUSES = ("available", "applied", "reviewing", "nominated", "scheduled", "completed",
            "accepted", "hired", "rejected", "withdrawn")
ALLOWED: dict[str, set[str]] = {
    "available": {"applied", "nominated"},
    "applied": {"reviewing", "nominated", "scheduled", "accepted", "rejected", "withdrawn"},
    "reviewing": {"nominated", "scheduled", "accepted", "rejected", "withdrawn"},
    "nominated": {"scheduled", "completed", "accepted", "rejected", "withdrawn"},
    "scheduled": {"completed", "accepted", "rejected", "withdrawn"},
    "completed": {"accepted", "rejected", "withdrawn"},
    "accepted": {"hired", "withdrawn"},
    "hired": set(), "rejected": set(), "withdrawn": set(),
}
# Steps the candidate takes themselves; the company takes the others.
CANDIDATE_STEPS = {"applied", "completed", "hired", "withdrawn"}
REACHED_INTERVIEW = {"nominated", "scheduled", "completed", "accepted", "hired"}


class RuleError(ValueError):
    """A request that breaks a business rule (shown to the user as-is)."""


def _skills(row) -> list[str]:
    return json.loads(row["skills_json"] or "[]")


def match_score(skills: list[str], required: list[str]) -> int:
    if not required:
        return 0
    owned = {s.strip().lower() for s in skills}
    return round(sum(1 for s in required if s.strip().lower() in owned) / len(required) * 100)


# ---------------------------------------------------------------- seed

def seed(conn: sqlite3.Connection, *, reset: bool = False) -> bool:
    """Load the demo company data when the tables are empty (or always with reset=True)."""
    if reset:
        conn.execute("DELETE FROM applications")
        conn.execute("DELETE FROM postings")
        conn.execute("DELETE FROM talents")
    elif conn.execute("SELECT COUNT(*) FROM postings").fetchone()[0]:
        return False
    data = json.loads(project_path(SEED_FILE).read_text(encoding="utf-8"))
    for p in data["postings"]:
        conn.execute(
            "INSERT INTO postings (id, company, title, city, mode, salary, description, skills_json, min_years)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (p["id"], data["company"], p["title"], p.get("city"), p.get("mode"), p.get("salary"),
             p.get("description"), json.dumps(p["skills"], ensure_ascii=False), p.get("min_years", 0)))
    for t in data["talents"]:
        conn.execute("INSERT INTO talents (id, name, mode, years, city, skills_json) VALUES (?, ?, ?, ?, ?, ?)",
                     (t["id"], t["name"], t["mode"], t["years"], t.get("city"),
                      json.dumps(t["skills"], ensure_ascii=False)))
    for a in data["applications"]:
        retained = a.get("retained")
        conn.execute(
            "INSERT INTO applications (posting_id, talent_id, status, interview_at, retained) VALUES (?, ?, ?, ?, ?)",
            (a["job"], a["talent"], a["status"], a.get("interview_at"),
             None if retained is None else int(retained)))
    log.info("[OK]    company demo data loaded: %d postings, %d talents, %d applications",
             len(data["postings"]), len(data["talents"]), len(data["applications"]))
    return True


@log_step(summary=lambda _: "demo data reset")
def reset_demo() -> None:
    with connect() as conn:
        seed(conn, reset=True)


# ---------------------------------------------------------------- postings

def _posting(row, counts: dict[str, int]) -> dict:
    return {"id": row["id"], "company": row["company"], "title": row["title"], "city": row["city"],
            "mode": row["mode"], "salary": row["salary"], "description": row["description"],
            "skills": _skills(row), "min_years": row["min_years"], "applicants": counts.get(row["id"], 0)}


@log_step(summary=lambda rows: f"{len(rows)} postings")
def list_postings() -> list[dict]:
    with connect() as conn:
        counts = dict(conn.execute(
            "SELECT posting_id, COUNT(*) FROM applications WHERE status != 'available' GROUP BY posting_id").fetchall())
        rows = conn.execute("SELECT * FROM postings WHERE source = 'company' ORDER BY created_at, rowid").fetchall()
    return [_posting(row, counts) for row in rows]


@log_step(summary=lambda p: f"posting_id={p['id']}")
def create_posting(title: str, skills: list[str], min_years: int, city: str | None = None,
                   mode: str | None = None, description: str | None = None) -> dict:
    title = title.strip()
    clean = list(dict.fromkeys(s.strip() for s in skills if s and s.strip()))
    if not title:
        raise RuleError("اكتب المسمى الوظيفي.")
    if not clean:
        raise RuleError("أضف مهارة مطلوبة واحدة على الأقل.")
    if not 0 <= min_years <= 30:
        raise RuleError("سنوات الخبرة غير صحيحة.")
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") or "job"
    posting_id = f"{slug}-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    with connect() as conn:
        company = conn.execute("SELECT company FROM postings LIMIT 1").fetchone()
        conn.execute(
            "INSERT INTO postings (id, company, title, city, mode, description, skills_json, min_years)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (posting_id, company[0] if company else "جهة التوظيف", title, city, mode, description,
             json.dumps(clean, ensure_ascii=False), min_years))
        row = conn.execute("SELECT * FROM postings WHERE id = ?", (posting_id,)).fetchone()
    return _posting(row, {})


@log_step()
def set_min_years(posting_id: str, min_years: int) -> None:
    if not 0 <= min_years <= 30:
        raise RuleError("سنوات الخبرة غير صحيحة.")
    with connect() as conn:
        if not conn.execute("UPDATE postings SET min_years = ? WHERE id = ?", (min_years, posting_id)).rowcount:
            raise KeyError(posting_id)


# ---------------------------------------------------------------- candidates

@log_step(summary=lambda rows: f"{len(rows)} candidates")
def rank_candidates(posting_id: str, min_years: int | None = None, must_have: list[str] | None = None) -> list[dict]:
    """Applicants ranked by match. A posting without applicants gets suggestions from the pool."""
    with connect() as conn:
        posting = conn.execute("SELECT * FROM postings WHERE id = ?", (posting_id,)).fetchone()
        if not posting:
            raise KeyError(posting_id)
        required = _skills(posting)
        min_years = posting["min_years"] if min_years is None else min_years
        rows = conn.execute(
            "SELECT t.*, a.status, a.interview_at, a.retained FROM talents t"
            " JOIN applications a ON a.talent_id = t.id AND a.posting_id = ?", (posting_id,)).fetchall()
        suggested = False
        if not rows:
            rows = [row for row in conn.execute(
                "SELECT t.*, 'available' AS status, NULL AS interview_at, NULL AS retained FROM talents t").fetchall()
                if match_score(_skills(row), required) > 0]
            suggested = True
    wanted = [s.strip().lower() for s in (must_have or []) if s.strip()]
    result = []
    for row in rows:
        skills = _skills(row)
        owned = {s.lower() for s in skills}
        if row["years"] < min_years or not all(s in owned for s in wanted):
            continue
        result.append({"talent": {"id": row["id"], "name": row["name"], "mode": row["mode"], "years": row["years"],
                                  "city": row["city"], "skills": skills},
                       "status": row["status"], "interview_at": row["interview_at"],
                       "match": match_score(skills, required), "suggested": suggested})
    return sorted(result, key=lambda c: (-c["match"], -c["talent"]["years"]))


def _current(conn, posting_id: str, talent_id: str) -> str:
    if not conn.execute("SELECT 1 FROM postings WHERE id = ?", (posting_id,)).fetchone():
        raise KeyError(posting_id)
    if not conn.execute("SELECT 1 FROM talents WHERE id = ?", (talent_id,)).fetchone():
        raise KeyError(talent_id)
    row = conn.execute("SELECT status FROM applications WHERE posting_id = ? AND talent_id = ?",
                       (posting_id, talent_id)).fetchone()
    return row["status"] if row else "available"


def _write(conn, posting_id: str, talent_id: str, status: str, interview_at: str | None = None) -> None:
    retained = 1 if status == "hired" else None
    conn.execute(
        "INSERT INTO applications (posting_id, talent_id, status, interview_at, retained) VALUES (?, ?, ?, ?, ?)"
        " ON CONFLICT (posting_id, talent_id) DO UPDATE SET status = excluded.status,"
        " interview_at = COALESCE(excluded.interview_at, applications.interview_at),"
        " retained = COALESCE(excluded.retained, applications.retained), updated_at = CURRENT_TIMESTAMP",
        (posting_id, talent_id, status, interview_at, retained))


def _has_cv(conn, talent_id: str) -> bool:
    """Applying needs a CV: an analysed profile, or (the demo pool) a talent record that already lists skills."""
    if conn.execute("SELECT 1 FROM cv_profiles WHERE candidate_id = ?", (talent_id,)).fetchone():
        return True
    row = conn.execute("SELECT skills_json FROM talents WHERE id = ?", (talent_id,)).fetchone()
    return bool(row and json.loads(row["skills_json"] or "[]"))


def _default_interview(conn, talent_id: str) -> str:
    """Default slot when a candidate is nominated: two days later, 10:00 Riyadh, skipping days with another interview."""
    taken = {r["interview_at"][:10] for r in conn.execute(
        "SELECT interview_at FROM applications WHERE talent_id = ? AND interview_at IS NOT NULL", (talent_id,)).fetchall()}
    riyadh = timezone(timedelta(hours=3))
    for offset in range(2, 60):
        day = (datetime.now(riyadh) + timedelta(days=offset)).date().isoformat()
        if day not in taken:
            return f"{day}T10:00:00+03:00"
    return (datetime.now(riyadh) + timedelta(days=60)).replace(hour=10, minute=0, second=0, microsecond=0).isoformat()


@log_step(summary=lambda s: f"status={s}")
def change_status(posting_id: str, talent_id: str, status: str, *, by: str = "company") -> str:
    if status not in STATUSES or status == "available":
        raise RuleError("حالة غير معروفة.")
    if by == "candidate" and status not in CANDIDATE_STEPS:
        raise RuleError("هذه الخطوة تتخذها الجهة.")
    if by == "company" and status in {"applied", "hired"}:
        raise RuleError("هذه الخطوة يتخذها المرشح.")
    with connect() as conn:
        current = _current(conn, posting_id, talent_id)
        if status not in ALLOWED[current]:
            raise RuleError(f"لا يمكن الانتقال من «{current}» إلى «{status}».")
        if status == "applied":
            job = conn.execute("SELECT status FROM postings WHERE id = ?", (posting_id,)).fetchone()
            if job and job["status"] != "active":
                raise RuleError("انتهى التقديم على هذه الوظيفة.")
            if not _has_cv(conn, talent_id):
                raise RuleError("أكمل تحليل سيرتك الذاتية قبل التقديم.")
        interview = None
        if status == "nominated":
            row = conn.execute("SELECT interview_at FROM applications WHERE posting_id = ? AND talent_id = ?", (posting_id, talent_id)).fetchone()
            if not (row and row["interview_at"]):
                interview = _default_interview(conn, talent_id)
        _write(conn, posting_id, talent_id, status, interview)
    return status


@log_step(summary=lambda s: f"scheduled {s}")
def schedule_interview(posting_id: str, talent_id: str, interview_at: str) -> str:
    try:
        when = datetime.fromisoformat(interview_at)
    except ValueError as exc:
        raise RuleError("اختر موعدًا صحيحًا.") from exc
    with connect() as conn:
        current = _current(conn, posting_id, talent_id)
        if current not in {"nominated", "scheduled"}:
            raise RuleError("رشّح المرشح للمقابلة قبل تحديد الموعد.")
        _write(conn, posting_id, talent_id, "scheduled", when.isoformat())
    return when.isoformat()


@log_step(summary=lambda rows: f"{len(rows)} applications")
def talent_applications(talent_id: str) -> list[dict]:
    with connect() as conn:
        rows = conn.execute("SELECT posting_id, status, interview_at FROM applications WHERE talent_id = ?",
                            (talent_id,)).fetchall()
    return [dict(row) for row in rows]


# ---------------------------------------------------------------- indicators

@log_step(summary=lambda i: f"applicants={i['applicants']} hired={i['hired']}")
def indicators(posting_id: str | None = None) -> dict:
    """Hiring indicators computed from the stored applications."""
    with connect() as conn:
        sql = ("SELECT a.status, a.retained, t.mode, t.skills_json AS talent_skills, p.skills_json AS posting_skills"
               " FROM applications a JOIN talents t ON t.id = a.talent_id JOIN postings p ON p.id = a.posting_id"
               " WHERE a.status != 'available'")
        rows = conn.execute(sql + (" AND a.posting_id = ?" if posting_id else ""),
                            (posting_id,) if posting_id else ()).fetchall()
        postings = conn.execute("SELECT COUNT(*) FROM postings WHERE source = 'company'").fetchone()[0]
    matches = [match_score(json.loads(r["talent_skills"]), json.loads(r["posting_skills"])) for r in rows]
    hired = [r for r in rows if r["status"] == "hired"]
    pct = lambda part, whole: round(part / whole * 100) if whole else 0  # noqa: E731
    return {
        "postings": postings,
        "applicants": len(rows),
        "average_match": round(sum(matches) / len(matches)) if matches else 0,
        "interview_rate": pct(sum(r["status"] in REACHED_INTERVIEW for r in rows), len(rows)),
        "hired": len(hired),
        "retention": pct(sum(r["retained"] != 0 for r in hired), len(hired)) if hired else None,
        # Applicants and hires per communication mode (deaf = sign, blind = voice).
        "by_mode": {mode: {"applicants": sum(r["mode"] == mode for r in rows),
                           "hired": sum(r["mode"] == mode for r in hired)} for mode in ("sign", "voice")},
    }
