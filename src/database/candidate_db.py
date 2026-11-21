"""Job agent storage: analysed CV profiles, job matches, agent runs (stages), and job postings from search.

Ported from the teammate's PostgreSQL tables (cv_profiles, job_matches, agent_runs, jobs) to our SQLite.
Discovered jobs are stored in the same `postings` table as the company's jobs, so both users see one list.
Nothing here logs CV text, names or e-mails: only ids and counts.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

from src.agent.text.arabic import normalize_arabic, unique_strings
from src.database.db import connect
from src.logger import get_logger, log_step

log = get_logger("database.candidate")

# Columns added to `postings` for jobs found by the search agent (existing databases are migrated in place).
_POSTING_COLUMNS = {
    "english": "TEXT", "source": "TEXT NOT NULL DEFAULT 'company'", "source_name": "TEXT", "source_url": "TEXT", "posted_at": "TEXT",
    "deadline": "TEXT", "fingerprint": "TEXT", "dedupe_key": "TEXT", "status": "TEXT NOT NULL DEFAULT 'active'",
    "deaf_friendly_reason": "TEXT", "updated_at": "TEXT",
}


def migrate(conn: sqlite3.Connection) -> None:
    if "cv_text" not in {row[1] for row in conn.execute("PRAGMA table_info(cv_profiles)")}:
        conn.execute("ALTER TABLE cv_profiles ADD COLUMN cv_text TEXT")
    have = {row[1] for row in conn.execute("PRAGMA table_info(postings)")}
    for column, kind in _POSTING_COLUMNS.items():
        if column not in have:
            conn.execute(f"ALTER TABLE postings ADD COLUMN {column} {kind}")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS postings_fingerprint ON postings(fingerprint) WHERE fingerprint IS NOT NULL")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------------------------------------------------------------- profiles and matches

@log_step(summary=lambda _: "profile saved")
def save_profile(candidate_id: str, profile: dict, parser_version: int, cv_text: str | None = None) -> None:
    """cv_text=None keeps the stored text (e.g. when only the reading is refreshed)."""
    with connect() as conn:
        conn.execute(
            "INSERT INTO cv_profiles (candidate_id, profile_json, engine, parser_version, cv_text, updated_at) VALUES (?, ?, ?, ?, ?, ?)"
            " ON CONFLICT (candidate_id) DO UPDATE SET profile_json = excluded.profile_json, engine = excluded.engine,"
            " parser_version = excluded.parser_version, cv_text = COALESCE(excluded.cv_text, cv_profiles.cv_text), updated_at = excluded.updated_at",
            (candidate_id, json.dumps(profile, ensure_ascii=False), profile.get("engine", "heuristic"), parser_version, cv_text, _now()))


def get_profile(candidate_id: str) -> dict | None:
    stored = get_stored_profile(candidate_id)
    return stored["profile"] if stored else None


def get_stored_profile(candidate_id: str) -> dict | None:
    """{profile, cv_text, parser_version, engine} — the text stays on the server (never returned by the API)."""
    with connect() as conn:
        row = conn.execute("SELECT * FROM cv_profiles WHERE candidate_id = ?", (candidate_id,)).fetchone()
    if not row:
        return None
    return {"profile": json.loads(row["profile_json"]), "cv_text": row["cv_text"] or "", "parser_version": row["parser_version"], "engine": row["engine"]}


def active_candidates(days: int = 60, limit: int = 50) -> list[str]:
    """Candidates whose CV was analysed in the last `days` days, newest first."""
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat(timespec="seconds")
    with connect() as conn:
        rows = conn.execute("SELECT candidate_id FROM cv_profiles WHERE updated_at > ? ORDER BY updated_at DESC LIMIT ?", (since, limit)).fetchall()
    return [r["candidate_id"] for r in rows]


def demand_roles(limit: int = 6) -> list[str]:
    """The roles that suit most analysed CVs (top two per CV), so the general search follows real demand."""
    counts: dict[str, int] = {}
    with connect() as conn:
        rows = conn.execute("SELECT profile_json FROM cv_profiles ORDER BY updated_at DESC LIMIT 300").fetchall()
    for row in rows:
        for role in json.loads(row["profile_json"]).get("suggestedRoles", [])[:2]:
            counts[role] = counts.get(role, 0) + 1
    return [role for role, _ in sorted(counts.items(), key=lambda item: -item[1])[:limit]]


@log_step(summary=lambda n: f"{n} matches saved")
def save_matches(candidate_id: str, matches: list[dict]) -> int:
    with connect() as conn:
        for m in matches:
            conn.execute(
                "INSERT INTO job_matches (candidate_id, job_id, score, reason, matched_json, missing_json, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)"
                " ON CONFLICT (candidate_id, job_id) DO UPDATE SET score = excluded.score, reason = excluded.reason,"
                " matched_json = excluded.matched_json, missing_json = excluded.missing_json, updated_at = excluded.updated_at",
                (candidate_id, m["job_id"], m["match"], m["reason"], json.dumps(m.get("matched_skills", []), ensure_ascii=False),
                 json.dumps(m.get("missing_skills", []), ensure_ascii=False), _now()))
    return len(matches)


def list_matches(candidate_id: str) -> list[dict]:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM job_matches WHERE candidate_id = ? ORDER BY score DESC", (candidate_id,)).fetchall()
    return [{"job_id": r["job_id"], "match": r["score"], "reason": r["reason"], "matched_skills": json.loads(r["matched_json"]),
             "missing_skills": json.loads(r["missing_json"])} for r in rows]


# ---------------------------------------------------------------- agent runs (pipeline stages)

STAGE_LABELS = {
    "extract": "استخراج نص السيرة من الملف",
    "read": "قراءة السيرة (ATS): الخبرات والتدريب والتطوع والمشاريع والمهارات",
    "ai": "قراءة Claude والتحقق من الأدلة في نص السيرة",
    "titles": "تحديد المسميات الوظيفية المناسبة",
    "match": "مطابقة الوظائف وحساب نسبة التوافق",
    "job_search": "البحث عن وظائف جديدة في المصادر الموثوقة",
}


def start_run(agent: str, candidate_id: str | None) -> int:
    with connect() as conn:
        cur = conn.execute("INSERT INTO agent_runs (agent, candidate_id, status, stats_json) VALUES (?, ?, 'running', '{}')", (agent, candidate_id))
        return int(cur.lastrowid)


def set_stats(run_id: int, stats: dict) -> None:
    with connect() as conn:
        conn.execute("UPDATE agent_runs SET stats_json = ? WHERE id = ?", (json.dumps(stats, ensure_ascii=False), run_id))


def finish_run(run_id: int, status: str, error: str | None = None, stats: dict | None = None) -> None:
    with connect() as conn:
        if stats is not None:
            conn.execute("UPDATE agent_runs SET stats_json = ? WHERE id = ?", (json.dumps(stats, ensure_ascii=False), run_id))
        conn.execute("UPDATE agent_runs SET status = ?, error = ?, finished_at = ? WHERE id = ?", (status, error, _now(), run_id))


def ran_recently(agent: str, candidate_id: str, hours: float) -> bool:
    since = (datetime.now(timezone.utc) - timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")
    with connect() as conn:
        row = conn.execute("SELECT 1 FROM agent_runs WHERE agent = ? AND candidate_id = ? AND started_at > ? LIMIT 1",
                           (agent, candidate_id, since)).fetchone()
    return row is not None


def recent_runs(limit: int = 20) -> list[dict]:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM agent_runs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [{"id": r["id"], "agent": r["agent"], "candidate_id": r["candidate_id"], "status": r["status"], "stats": json.loads(r["stats_json"] or "{}"),
             "error": r["error"], "started_at": r["started_at"], "finished_at": r["finished_at"]} for r in rows]


def any_run_succeeded(agent: str) -> bool:
    with connect() as conn:
        return conn.execute("SELECT 1 FROM agent_runs WHERE agent = ? AND status = 'succeeded' LIMIT 1", (agent,)).fetchone() is not None


def latest_runs(candidate_id: str) -> list[dict]:
    """The latest CV analysis (its stages) and the latest job searches for one candidate."""
    with connect() as conn:
        rows = conn.execute("SELECT * FROM agent_runs WHERE candidate_id = ? ORDER BY id DESC LIMIT 10", (candidate_id,)).fetchall()
    out, seen = [], set()
    for r in rows:
        if r["agent"] in seen:
            continue
        seen.add(r["agent"])
        out.append({"agent": r["agent"], "status": r["status"], "stats": json.loads(r["stats_json"] or "{}"), "error": r["error"],
                    "started_at": r["started_at"], "finished_at": r["finished_at"]})
    return out


class CvPipeline:
    """Tracks one CV through the agents, stage by stage (agent_runs, agent = 'cv')."""

    def __init__(self, candidate_id: str):
        self.candidate_id = candidate_id
        self.run_id = start_run("cv", candidate_id)
        self.stages: list[dict] = []

    def stage(self, name: str, status: str, detail: str = "") -> None:
        entry = {"name": name, "label": STAGE_LABELS[name], "status": status, "detail": detail[:300], "at": _now()}
        self.stages = [*(s for s in self.stages if s["name"] != name), entry]
        set_stats(self.run_id, {"stages": self.stages})
        log.info("[STAGE] cv %s:%s run=%s", name, status, self.run_id)

    def finish(self, status: str, error: str | None = None) -> None:
        finish_run(self.run_id, status, error, {"stages": self.stages})


# ---------------------------------------------------------------- postings found by the search agent

def fingerprint_of(title: str, company: str, source_url: str) -> str:
    try:
        parsed = urlparse(source_url)
        url = f"{parsed.netloc}{parsed.path}".lower() if parsed.netloc else ""
    except ValueError:
        url = ""
    return hashlib.sha256(f"{normalize_arabic(title)}|{normalize_arabic(company)}|{url}".encode()).hexdigest()[:32]


def dedupe_key_of(title: str, company: str) -> str:
    """Same job on several sites: same title at the same organisation."""
    org = re.sub(r"^(شركه|مؤسسه|مجموعه)\s+", "", normalize_arabic(company))
    org = re.sub(r"\s+", " ", re.sub(r"\b(company|co|ltd|llc|inc|corp|corporation|group|holding)\b\.?", " ", org, flags=re.ASCII)).strip()
    return hashlib.sha256(f"{normalize_arabic(title)}|{org}".encode()).hexdigest()[:32]


def _strip(value: str | None, limit: int) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]*>", " ", value or "")).strip()[:limit]


def _valid_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


@log_step(summary=lambda r: f"created={r['created']} updated={r['updated']} skipped={r['skipped']}")
def ingest_postings(postings: list[dict], source: str) -> dict:
    """Validates, normalises and upserts postings into the same table as the company's jobs."""
    from src.agent.job_agent.ats.skills import canonical_skill, find_skills

    created = updated = skipped = 0
    reasons: list[str] = []
    now = datetime.now(timezone.utc)
    with connect() as conn:
        for p in postings:
            title, company = _strip(p.get("title"), 120), _strip(p.get("company"), 120)
            url = p.get("sourceUrl") or ""
            source_url = url if urlparse(url).scheme in ("http", "https") and urlparse(url).netloc else ""
            deadline = _valid_date(p.get("deadline"))
            problem = ("لا يوجد مسمى" if not title else "لا توجد جهة" if not company else "رابط غير صالح" if not source_url
                       else "انتهى موعد التقديم" if deadline and deadline < now else "")
            if problem:
                skipped += 1
                reasons.append(problem)
                continue
            description = _strip(p.get("description"), 600) or f"وظيفة {title} لدى {company}."
            listed = [s for s in (_strip(x, 60) for x in p.get("skills", [])) if s]
            listed_ids = {normalize_arabic(canonical_skill(s)) for s in listed}
            skills = unique_strings([*listed, *(s for s in find_skills(description) if normalize_arabic(s) not in listed_ids)], 10)
            fingerprint, dedupe_key = fingerprint_of(title, company, source_url), dedupe_key_of(title, company)
            same = conn.execute("SELECT id FROM postings WHERE dedupe_key = ? AND status = 'active' AND fingerprint != ? LIMIT 1",
                                (dedupe_key, fingerprint)).fetchone()
            if same:
                conn.execute("UPDATE postings SET updated_at = ? WHERE id = ?", (_now(), same["id"]))
                updated += 1
                continue
            values = (title, _strip(p.get("english"), 120), company, _strip(p.get("location"), 60) or "غير محدد", p.get("mode") or "حضوري",
                      _strip(p.get("salary"), 60), description, json.dumps(skills, ensure_ascii=False), 0, source,
                      _strip(p.get("sourceName"), 80) or None, source_url, p.get("postedAt"), deadline.isoformat() if deadline else None,
                      dedupe_key, _strip(p.get("deafFriendlyReason"), 300) or None, _now())
            exists = conn.execute("SELECT id FROM postings WHERE fingerprint = ?", (fingerprint,)).fetchone()
            if exists:
                conn.execute("UPDATE postings SET title=?, english=?, company=?, city=?, mode=?, salary=?, description=?, skills_json=?, min_years=?,"
                             " source=?, source_name=?, source_url=?, posted_at=?, deadline=?, dedupe_key=?, deaf_friendly_reason=?, updated_at=?,"
                             " status='active' WHERE id = ?", (*values, exists["id"]))
                updated += 1
            else:
                conn.execute("INSERT INTO postings (title, english, company, city, mode, salary, description, skills_json, min_years, source,"
                             " source_name, source_url, posted_at, deadline, dedupe_key, deaf_friendly_reason, updated_at, id, fingerprint, status)"
                             " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active')",
                             (*values, f"job-{fingerprint[:12]}", fingerprint))
                created += 1
    return {"created": created, "updated": updated, "skipped": skipped, "received": len(postings), "reasons": reasons}


def expire_old_postings(days: int = 45) -> int:
    """Discovered jobs end after their deadline, or after `days` without an update. Company jobs never expire here."""
    now = datetime.now(timezone.utc)
    stale = (now - timedelta(days=days)).isoformat(timespec="seconds")
    with connect() as conn:
        cur = conn.execute("UPDATE postings SET status = 'expired', updated_at = ? WHERE status = 'active' AND source NOT IN ('company', 'sanad')"
                           " AND ((deadline IS NOT NULL AND deadline < ?) OR (deadline IS NULL AND updated_at < ?))",
                           (_now(), now.isoformat(timespec="seconds"), stale))
        return cur.rowcount


def active_postings() -> list[dict]:
    """Every active job (company + discovered) in the job agent's shape."""
    with connect() as conn:
        try:
            rows = conn.execute("SELECT * FROM postings WHERE status = 'active' ORDER BY created_at, rowid").fetchall()
        except sqlite3.OperationalError:   # tables not created yet (unit tests without init_db)
            return []
    return [{"id": r["id"], "title": r["title"], "english": r["english"] or "", "company": r["company"], "city": r["city"], "mode": r["mode"],
             "salary": r["salary"], "description": r["description"] or "", "skills": json.loads(r["skills_json"] or "[]"), "min_years": r["min_years"],
             "source": r["source"], "source_name": r["source_name"], "source_url": r["source_url"]} for r in rows]
