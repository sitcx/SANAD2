"""Candidate service: one CV through the whole Job Agent, stage by stage (the teammate's pipeline, in Python).

    1 extract  text from the PDF / Word file          4 titles      job titles that suit the CV
    2 read     offline ATS reading (roles, skills…)    5 match       match % for every active job (company + found)
    3 ai       Claude's reading, verified             6 job_search  public sources + Claude web search (background)
The profile is stored per candidate; for a talent of the company pool, their skills and years are updated too,
so the company ranks the candidate by what the CV really says. Logs carry ids and counts only.
"""
from __future__ import annotations

import os
import threading

from src.agent.job_agent.ats.reader import PARSER_VERSION, looks_like_cv
from src.agent.job_agent.graph import recommend_jobs
from src.agent.job_agent.tools._text import canonical_city
from src.agent.job_agent.tools.read_cv import cv_text
from src.database import candidate_db
from src.database.db import connect
from src.logger import get_logger

log = get_logger("job_agent.service")


def sources_enabled() -> bool:
    return os.getenv("SANAD_DISABLE_JOB_SOURCES") != "1"


def _talent_mode(candidate_id: str) -> str:
    with connect() as conn:
        row = conn.execute("SELECT mode FROM talents WHERE id = ?", (candidate_id,)).fetchone()
    return row["mode"] if row else "sign"


def _update_talent(candidate_id: str, profile: dict) -> None:
    """The company sees the candidate's real skills and years from the analysed CV."""
    import json

    with connect() as conn:
        conn.execute("UPDATE talents SET skills_json = ?, years = ? WHERE id = ?",
                     (json.dumps(profile.get("skills", [])[:20], ensure_ascii=False), int(profile.get("yearsExperience") or 0), candidate_id))


def _save_matches(candidate_id: str, result: dict) -> int:
    return candidate_db.save_matches(candidate_id, result.get("jobs", []))


def rematch_all(candidate_id: str, profile: dict, text: str = "") -> int:
    """Re-matches every active job for this candidate (after new jobs arrive or the reading improves)."""
    from src.agent.job_agent.tools.score_job import score_job
    from src.agent.job_agent.tools.search_jobs import catalogue

    short = {"skills": profile.get("skills", []), "experience_years": profile.get("yearsExperience"),
             "city": canonical_city(((profile.get("ats") or {}).get("contact") or {}).get("city")), "ats_profile": profile}
    return _save_matches(candidate_id, {"jobs": [score_job(short, job, text) for job in catalogue()]})


def upgrade_stale_profile(candidate_id: str) -> bool:
    """A profile read by an older reader version is re-read from the stored CV text (no new upload needed).
    Claude's earlier reading is kept; the offline reader fills it again and re-scores the file for ATS."""
    from src.agent.job_agent.ats.reader import heuristic_profile, merge_profiles

    stored = candidate_db.get_stored_profile(candidate_id)
    if not stored or stored["parser_version"] >= PARSER_VERSION or not stored["cv_text"].strip():
        return False
    offline = heuristic_profile(stored["cv_text"])
    profile = merge_profiles({**stored["profile"], "ats": None}, offline) if stored["engine"] == "claude" else offline
    candidate_db.save_profile(candidate_id, profile, PARSER_VERSION)
    _update_talent(candidate_id, profile)
    rematch_all(candidate_id, profile, stored["cv_text"])
    log.info("[OK]    profile re-read with reader v%d for candidate=%s", PARSER_VERSION, candidate_id)
    return True


def refresh_in_background(candidate_id: str) -> None:
    """On opening the profile: refresh this candidate's jobs from the public sources (at most every 6 hours)."""
    from src.agent.job_agent.search.discovery import SOURCES_COOLDOWN_HOURS

    if not sources_enabled() or candidate_db.ran_recently("jobs-sources", candidate_id, SOURCES_COOLDOWN_HOURS):
        return
    stored = candidate_db.get_stored_profile(candidate_id)
    if not stored:
        return

    def work() -> None:
        from src.agent.job_agent.search.discovery import discover_from_sources

        try:
            outcome = discover_from_sources(candidate_id, stored["profile"], stored["cv_text"], mode=_talent_mode(candidate_id))
            if outcome["status"] == "done":
                rematch_all(candidate_id, stored["profile"], stored["cv_text"])
        except Exception as exc:  # noqa: BLE001 - a background refresh must never break the page
            log.warning("[FAIL]  background job refresh candidate=%s -> %s", candidate_id, type(exc).__name__)

    threading.Thread(target=work, daemon=True, name=f"job-refresh-{candidate_id}").start()


BASE_QUERIES = [
    "وظائف للصم وضعاف السمع السعودية", "وظائف للمكفوفين وضعاف البصر السعودية", "وظائف ذوي الإعاقة السمعية", "جدارات وظائف الأشخاص ذوي الإعاقة",
    "وظائف ذوي الإعاقة الرياض", "وظائف ذوي الإعاقة جدة", "وظائف ذوي الإعاقة الدمام الخبر", "وظائف عن بعد لذوي الإعاقة السعودية",
    "برنامج توافق توظيف ذوي الإعاقة وظائف", "Saudi Arabia jobs for deaf and hard of hearing", "Saudi Arabia jobs for blind and visually impaired",
    "Saudi Arabia jobs persons with disabilities inclusive employer",
]
_general_lock = threading.Lock()


def run_jobs_agent(trigger: str) -> dict:
    """The general search (schedule or admin): Claude web search with demand-led queries, feeds, a fresh source search
    for each active candidate (each at most every 6 hours), then expired jobs are closed. Recorded as agent "jobs"."""
    from src.agent.inference.llm import llm_available
    from src.agent.job_agent.search.discovery import discover_from_sources, discover_with_claude
    from src.agent.job_agent.search.feeds import fetch_feeds
    from src.agent.text.arabic import unique_strings

    if not _general_lock.acquire(blocking=False):
        return {"status": "already_running"}
    run_id = candidate_db.start_run("jobs", None)
    stats: dict = {"trigger": trigger}
    try:
        if llm_available("job_agent"):
            queries = unique_strings([*BASE_QUERIES, *(f"وظيفة {role} ذوي الإعاقة السعودية" for role in candidate_db.demand_roles())])
            try:
                stats["claude"] = discover_with_claude(queries)
            except Exception as exc:  # noqa: BLE001
                stats["claudeError"] = type(exc).__name__
        if os.getenv("JOB_FEEDS"):
            stats["feeds"] = candidate_db.ingest_postings(fetch_feeds(), "feed")
        if sources_enabled():
            searched = 0
            for candidate_id in candidate_db.active_candidates():
                stored = candidate_db.get_stored_profile(candidate_id)
                if not stored:
                    continue
                outcome = discover_from_sources(candidate_id, stored["profile"], stored["cv_text"], mode=_talent_mode(candidate_id))
                if outcome["status"] == "done":
                    rematch_all(candidate_id, stored["profile"], stored["cv_text"])
                    searched += 1
            stats["sources"] = {"candidates": searched}
        stats["expired"] = candidate_db.expire_old_postings()
        candidate_db.finish_run(run_id, "succeeded", stats=stats)
        return {"status": "done", **stats}
    except Exception as exc:
        candidate_db.finish_run(run_id, "failed", type(exc).__name__, stats)
        raise
    finally:
        _general_lock.release()


_scheduler_started = False


def start_scheduler() -> None:
    """Runs the general search every JOBS_AGENT_INTERVAL_HOURS (default 12; 0 turns it off). The first run comes
    30 seconds after start-up if it never succeeded. Off when job sources are disabled (tests)."""
    global _scheduler_started
    hours = float(os.getenv("JOBS_AGENT_INTERVAL_HOURS") or 12)
    if _scheduler_started or hours <= 0 or not sources_enabled():
        return
    _scheduler_started = True

    def loop() -> None:
        stop = threading.Event()
        if not stop.wait(30) and not candidate_db.any_run_succeeded("jobs"):
            _safe_run("schedule")
        while not stop.wait(hours * 3600):
            _safe_run("schedule")

    threading.Thread(target=loop, daemon=True, name="jobs-agent-scheduler").start()
    log.info("[OK]    jobs agent scheduled every %s hours", hours)


def _safe_run(trigger: str) -> None:
    try:
        run_jobs_agent(trigger)
    except Exception as exc:  # noqa: BLE001 - the schedule keeps going
        log.warning("[FAIL]  scheduled jobs agent -> %s", type(exc).__name__)


def search_jobs_for(candidate_id: str, profile: dict, text: str, pipeline: candidate_db.CvPipeline | None = None) -> dict:
    """Public sources, then Claude web search; afterwards every job is re-matched for this candidate."""
    from src.agent.job_agent.search.discovery import discover_for_candidate, discover_from_sources

    outcomes = []
    if sources_enabled():
        outcomes.append(discover_from_sources(candidate_id, profile, text, mode=_talent_mode(candidate_id), force=pipeline is not None))
        outcomes.append(discover_for_candidate(candidate_id, profile))
    else:
        outcomes.append({"status": "skipped", "reason": "مصادر الوظائف معطلة (SANAD_DISABLE_JOB_SOURCES)"})
    done = any(o["status"] == "done" for o in outcomes)
    reason = " · ".join(o["reason"] for o in outcomes if o.get("reason"))
    if done:
        rematch_all(candidate_id, profile, text)
    if pipeline:
        pipeline.stage("job_search", "done" if done else "skipped", reason)
        pipeline.finish("succeeded")
    return {"status": "done" if done else "skipped", "reason": reason}


def _claude_available() -> bool:
    from src.agent.inference.llm import llm_available

    return llm_available("job_agent")


def _analyse_scanned_pdf(candidate_id: str, cv_file: str, pipeline: candidate_db.CvPipeline, answers: dict, background_search: bool) -> dict:
    """A scanned PDF: Claude reads the file, then the same matching and job search as any CV."""
    from pathlib import Path

    from src.agent.job_agent.ats.reader import read_scanned_pdf

    pipeline.stage("extract", "done", "صورة ممسوحة: يقرؤها Claude من ملف PDF مباشرة")
    try:
        ats, reading = read_scanned_pdf(Path(cv_file).read_bytes(), Path(cv_file).name)
    except Exception as exc:  # noqa: BLE001
        log.warning("[FAIL]  scanned PDF reading -> %s", type(exc).__name__)
        pipeline.stage("ai", "failed", f"تعذّرت قراءة Claude ({type(exc).__name__})")
        pipeline.finish("failed", "empty_text")
        return {"status": "failed", "error": "تعذّر قراءة نص السيرة (قد تكون صورة ممسوحة). ارفع ملفًا نصيًا PDF أو Word.", "stages": pipeline.stages}
    for name, (status, detail) in reading.items():
        pipeline.stage(name, status, detail)
    if not looks_like_cv(ats):
        pipeline.finish("failed", "nothing_found")
        return {"status": "failed", "error": "لم نجد مهارات أو خبرات واضحة في الملف. تأكد أنه سيرة ذاتية.", "stages": pipeline.stages}
    pipeline.stage("titles", "done" if ats["suggestedRoles"] else "skipped", "، ".join(ats["suggestedRoles"]) or "لا توجد بيانات كافية لاقتراح مسميات")
    candidate_db.save_profile(candidate_id, ats, PARSER_VERSION, "")
    _update_talent(candidate_id, ats)
    short = {"skills": ats["skills"], "experience_years": ats.get("yearsExperience"), "major": (ats["education"][0].split(" · ")[0] if ats["education"] else None),
             "city": canonical_city(answers.get("city")) if answers.get("city") else None, "ats_profile": ats}
    result = recommend_jobs(profile=short, answers=answers)
    if result.get("missing_info"):
        pipeline.stage("match", "skipped", "بانتظار إجابة المرشح عن: " + "، ".join(result["missing_info"]))
        pipeline.finish("succeeded")
        return {"status": "need_info", **result, "stages": pipeline.stages}
    pipeline.stage("match", "done", f"حُسبت نسبة التوافق لـ {rematch_all(candidate_id, ats)} وظيفة")
    if background_search:
        pipeline.stage("job_search", "running", "البحث في مصادر الوظائف بمسميات السيرة ومهاراتها")
        threading.Thread(target=search_jobs_for, args=(candidate_id, ats, "", pipeline), daemon=True).start()
    else:
        pipeline.stage("job_search", "skipped", "لم يُطلب البحث")
        pipeline.finish("succeeded")
    return {"status": "ok", **result, "stages": pipeline.stages}


def analyse_cv(candidate_id: str, cv_file: str, answers: dict | None = None, *, background_search: bool = True) -> dict:
    """Runs the pipeline for one uploaded CV. Returns the Job Agent result plus the stages."""
    pipeline = candidate_db.CvPipeline(candidate_id)
    try:
        try:
            text = cv_text(cv_file) if not cv_file.lower().endswith(".json") else ""
        except Exception as exc:  # noqa: BLE001 - a corrupt PDF / Word file is an unreadable CV, not a server error
            log.warning("[FAIL]  CV text extraction -> %s", type(exc).__name__)
            text = ""
        scanned = not cv_file.lower().endswith(".json") and len("".join(text.split())) < 40
        if scanned and cv_file.lower().endswith(".pdf") and _claude_available():
            return _analyse_scanned_pdf(candidate_id, cv_file, pipeline, answers or {}, background_search)
        if scanned:
            pipeline.stage("extract", "failed", "لا يوجد نص قابل للقراءة في الملف")
            pipeline.finish("failed", "empty_text")
            return {"status": "failed", "error": "تعذّر قراءة نص السيرة (قد تكون صورة ممسوحة). ارفع ملفًا نصيًا PDF أو Word.",
                    "stages": pipeline.stages}
        pipeline.stage("extract", "done", f"{len(text)} حرفًا")
        result = recommend_jobs(cv_file=cv_file, answers=answers or {})
        result.pop("cv_text", None)   # the CV text never leaves the server
        profile = result["profile"]
        ats = profile.get("ats_profile")
        for name, stage in (profile.get("reading") or {}).items():
            pipeline.stage(name, stage["status"], stage["detail"])
        if ats is not None and not looks_like_cv(ats):
            pipeline.finish("failed", "nothing_found")
            return {"status": "failed", "error": "لم نجد مهارات أو خبرات واضحة في الملف. تأكد أنه سيرة ذاتية.", "stages": pipeline.stages}
        if ats:
            pipeline.stage("titles", "done" if ats["suggestedRoles"] else "skipped",
                           "، ".join(ats["suggestedRoles"]) or "لا توجد بيانات كافية لاقتراح مسميات")
            candidate_db.save_profile(candidate_id, ats, PARSER_VERSION, text)
            _update_talent(candidate_id, ats)
        if result.get("missing_info"):
            pipeline.stage("match", "skipped", "بانتظار إجابة المرشح عن: " + "، ".join(result["missing_info"]))
            pipeline.finish("succeeded")
            return {"status": "need_info", **result, "stages": pipeline.stages}
        saved = _save_matches(candidate_id, result)
        pipeline.stage("match", "done", f"حُسبت نسبة التوافق لـ {saved} وظيفة")
        if ats and background_search:
            pipeline.stage("job_search", "running", "البحث في مصادر الوظائف بمسميات السيرة ومهاراتها")
            threading.Thread(target=search_jobs_for, args=(candidate_id, ats, text, pipeline), daemon=True,
                             name=f"job-search-{candidate_id}").start()
        else:
            pipeline.stage("job_search", "skipped", "لم يُطلب البحث")
            pipeline.finish("succeeded")
        return {"status": "ok", **result, "stages": pipeline.stages}
    except Exception as exc:
        log.error("[FAIL]  CV pipeline candidate=%s -> %s", candidate_id, type(exc).__name__)
        pipeline.finish("failed", type(exc).__name__)
        raise
