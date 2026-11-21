"""Candidate endpoints for the Job Agent (CV reading, matches, job search). Included by src/agent/api.py.

    POST /candidate/{talent_id}/cv              multipart: cv (pdf / doc / docx), answers (JSON, optional)
    GET  /candidate/{talent_id}/profile         analysed profile + ATS report, matches with job details, latest runs (stages)
    POST /candidate/{talent_id}/jobs/discover   search the job sources now (cooldowns apply unless the CV was just analysed)
    POST /admin/agents/jobs/run · GET /admin/agents/runs · POST /admin/jobs   (header X-Sanad-Admin)
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, Header, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool

from src.agent.job_agent import service
from src.database import candidate_db
from src.logger import get_logger

log = get_logger("candidate_api")
router = APIRouter()
CV_SUFFIXES = {".pdf", ".doc", ".docx"}   # like the teammate's service: PDF or Word only
MAX_CV_BYTES = 10 * 1024 * 1024
_PUBLIC_KEYS = ("status", "error", "profile", "missing_info", "widened", "jobs", "recommended", "stages")


def _valid_id(talent_id: str) -> str:
    if not talent_id or len(talent_id) > 64 or not all(c.isalnum() or c in "-_" for c in talent_id):
        raise HTTPException(422, "invalid candidate id")
    return talent_id


@router.post("/candidate/{talent_id}/cv")
async def upload_cv(talent_id: str, cv: UploadFile = File(...), answers: str | None = Form(None)) -> dict:
    """Reads the CV like an ATS, matches every active job, and starts a job search in the background."""
    _valid_id(talent_id)
    suffix = Path(cv.filename or "").suffix.lower()
    if suffix not in CV_SUFFIXES:
        raise HTTPException(415, "اختر ملف PDF أو Word.")
    content = await cv.read()
    if not content:
        raise HTTPException(422, "الملف فارغ. اختر سيرة ذاتية أخرى.")
    if len(content) > MAX_CV_BYTES:
        raise HTTPException(413, "يرجى اختيار ملف أصغر من ١٠ ميجابايت.")
    if suffix == ".pdf" and not content.startswith(b"%PDF"):
        raise HTTPException(415, "محتوى الملف لا يطابق نوعه. اختر ملف PDF أو Word صحيحًا.")
    ole, zipped = bytes([0xD0, 0xCF]), b"PK"   # legacy Word (OLE) and Word 2007+ (zip) file signatures
    if (suffix == ".docx" and not content.startswith(zipped)) or (suffix == ".doc" and not content.startswith((ole, zipped))):
        raise HTTPException(415, "محتوى الملف لا يطابق نوعه. اختر ملف PDF أو Word صحيحًا.")
    try:
        answers_data = json.loads(answers) if answers else {}
    except json.JSONDecodeError as exc:
        raise HTTPException(422, "answers must be JSON") from exc
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        path = Path(tmp.name)
    try:
        result = await run_in_threadpool(service.analyse_cv, talent_id, str(path), answers_data,
                                         background_search=service.sources_enabled())
    finally:
        path.unlink(missing_ok=True)
    if result["status"] == "failed":
        raise HTTPException(422, result["error"])
    return {k: result[k] for k in _PUBLIC_KEYS if k in result}


@router.get("/candidate/{talent_id}/profile")
async def get_profile(talent_id: str) -> dict:
    """Also re-reads a profile from an older reader version, and refreshes the jobs in the background (every 6 hours at most)."""
    from src.agent.inference.llm import llm_available
    from src.agent.job_agent.search.discovery import SOURCES

    _valid_id(talent_id)
    await run_in_threadpool(service.upgrade_stale_profile, talent_id)
    service.refresh_in_background(talent_id)
    profile = await run_in_threadpool(candidate_db.get_profile, talent_id)
    matches = await run_in_threadpool(candidate_db.list_matches, talent_id)
    jobs = {job["id"]: job for job in await run_in_threadpool(candidate_db.active_postings)}
    return {
        "profile": profile,
        "matches": [{**m, "job": jobs[m["job_id"]]} for m in matches if m["job_id"] in jobs],
        "runs": await run_in_threadpool(candidate_db.latest_runs, talent_id),
        "webSearchEnabled": llm_available("job_agent"),
        "sources": SOURCES,
    }


@router.post("/candidate/{talent_id}/jobs/discover")
async def discover(talent_id: str) -> dict:
    _valid_id(talent_id)
    stored = await run_in_threadpool(candidate_db.get_stored_profile, talent_id)
    if not stored:
        raise HTTPException(404, "ارفع سيرتك الذاتية أولًا.")
    return await run_in_threadpool(service.search_jobs_for, talent_id, stored["profile"], stored["cv_text"])


# ---------------------------------------------------------------- admin (header X-Sanad-Admin = SANAD_ADMIN_TOKEN; off when unset)

def _require_admin(token: str | None) -> None:
    import hmac
    import os

    expected = os.getenv("SANAD_ADMIN_TOKEN")
    if not expected or not token or not hmac.compare_digest(token, expected):
        raise HTTPException(403, "للمشرفين فقط.")


@router.post("/admin/agents/jobs/run")
async def admin_run_jobs_agent(x_sanad_admin: str | None = Header(None)) -> dict:
    _require_admin(x_sanad_admin)
    return await run_in_threadpool(service.run_jobs_agent, "manual")


@router.get("/admin/agents/runs")
async def admin_runs(x_sanad_admin: str | None = Header(None)) -> dict:
    _require_admin(x_sanad_admin)
    return {"runs": await run_in_threadpool(candidate_db.recent_runs)}


@router.post("/admin/jobs")
async def admin_add_jobs(body: dict, x_sanad_admin: str | None = Header(None)) -> dict:
    """{"jobs": [posting, ...]} (up to 200), stored like any job (source "employer")."""
    from pydantic import ValidationError

    from src.agent.job_agent.search.discovery import Posting

    _require_admin(x_sanad_admin)
    items = body.get("jobs")
    if not isinstance(items, list) or len(items) > 200:
        raise HTTPException(422, "jobs must be a list of up to 200 postings")
    try:
        postings = [Posting.model_validate(item).model_dump() for item in items]
    except ValidationError as exc:
        raise HTTPException(422, "invalid posting") from exc
    return await run_in_threadpool(candidate_db.ingest_postings, postings, "employer")
