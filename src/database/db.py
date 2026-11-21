"""SQLite connection and queries for Sanad."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from src.agent.core.config import get_config, project_path
from src.logger import get_logger, log_step

SCHEMA = Path(__file__).with_name("schema.sql")
log = get_logger("database.db")


def connect() -> sqlite3.Connection:
    """Open the database file named in config.yaml (database.path)."""
    path = project_path(get_config()["database"]["path"])
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@log_step(summary=lambda _: "tables ready, jobs.json loaded")
def init_db() -> None:
    """Create the tables from schema.sql and load jobs.json into the jobs table."""
    with connect() as conn:
        conn.executescript(SCHEMA.read_text(encoding="utf-8"))
        jobs_file = project_path(get_config()["job_agent"]["jobs_file"])
        for job in json.loads(jobs_file.read_text(encoding="utf-8")):
            conn.execute(
                "INSERT OR REPLACE INTO jobs (id, title, company, city, mode, description, skills_json)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (job["id"], job["title"], job.get("company"), job.get("city"), job.get("mode"),
                 job.get("description"), json.dumps(job.get("skills", []), ensure_ascii=False)))
        from src.database.company_db import seed   # local import: company_db imports this module
        seed(conn)


@log_step(summary=lambda cid: f"candidate_id={cid}")
def save_candidate(name: str, profile: dict) -> int:
    """Store a candidate and the read_cv profile; return the new id."""
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO candidates (name, city, profile_json) VALUES (?, ?, ?)",
            (name, profile.get("city"), json.dumps(profile, ensure_ascii=False)))
        return int(cur.lastrowid)


@log_step(summary=lambda jobs: f"{len(jobs)} jobs")
def list_jobs() -> list[dict]:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM jobs ORDER BY id").fetchall()
    return [{**{k: row[k] for k in row.keys() if k != "skills_json"},
             "skills": json.loads(row["skills_json"] or "[]")} for row in rows]


@log_step(summary=lambda iid: f"interview_id={iid}")
def start_interview(candidate_id: int | None, job_id: str | None, mode: str) -> int:
    """Create an interview row; return its id."""
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO interviews (candidate_id, job_id, mode) VALUES (?, ?, ?)",
            (candidate_id, job_id, mode))
        return int(cur.lastrowid)


_INTERVIEW_FIELDS = {"mode", "none_count", "interpreter_called", "interpreter_reason"}


@log_step()
def update_interview(interview_id: int, **fields) -> None:
    """Update counters/flags of an interview, e.g. update_interview(1, none_count=2)."""
    log.info("[INPUT] interview_id=%s %s", interview_id, fields)
    unknown = set(fields) - _INTERVIEW_FIELDS
    if unknown:
        raise ValueError(f"unknown interview fields: {sorted(unknown)}")
    if not fields:
        return
    if "interpreter_called" in fields:
        fields["interpreter_called"] = int(bool(fields["interpreter_called"]))
    assignments = ", ".join(f"{key} = ?" for key in fields)
    with connect() as conn:
        conn.execute(f"UPDATE interviews SET {assignments} WHERE id = ?", (*fields.values(), interview_id))


@log_step(summary=lambda row: "found" if row else "not found")
def get_interview(interview_id: int) -> dict | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM interviews WHERE id = ?", (interview_id,)).fetchone()
    return dict(row) if row else None
