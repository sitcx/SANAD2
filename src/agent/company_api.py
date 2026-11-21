"""Company and candidate-application endpoints (included by src/agent/api.py).

    GET  /company/indicators                         hiring indicators (optional ?job_id=)
    GET  /company/jobs                               postings with applicant counts
    POST /company/jobs                               {title, skills[], min_years, city?, mode?, description?}
    PUT  /company/jobs/{job_id}/min-years            {min_years}
    GET  /company/jobs/{job_id}/candidates           ?min_years=&must_have=a&must_have=b
    POST /company/jobs/{job_id}/candidates/{talent_id}/status     {status}
    POST /company/jobs/{job_id}/candidates/{talent_id}/schedule   {interview_at}
    POST /company/reset                              reload the demo data
    GET  /candidate/{talent_id}/applications
    POST /candidate/{talent_id}/applications/{job_id}   {status}  (applied | completed | hired | withdrawn)
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from src.database import company_db
from src.database.company_db import RuleError

router = APIRouter()


class NewJob(BaseModel):
    title: str = Field(max_length=120)
    skills: list[Annotated[str, Field(max_length=60)]] = Field(max_length=20)
    min_years: int = Field(ge=0, le=30)
    city: str | None = Field(None, max_length=60)
    mode: str | None = Field(None, max_length=30)
    description: str | None = Field(None, max_length=1000)


class StatusChange(BaseModel):
    status: str = Field(max_length=20)


class Schedule(BaseModel):
    interview_at: str = Field(max_length=40)


class MinYears(BaseModel):
    min_years: int = Field(ge=0, le=30)


async def _call(fn, *args, **kwargs):
    """Run a storage call; rule errors become 422 (Arabic message), unknown ids 404."""
    try:
        return await run_in_threadpool(fn, *args, **kwargs)
    except RuleError as exc:
        raise HTTPException(422, str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(404, f"not found: {exc.args[0]}") from exc


@router.get("/company/indicators")
async def get_indicators(job_id: str | None = None) -> dict:
    return await _call(company_db.indicators, job_id)


@router.get("/company/jobs")
async def get_jobs() -> list[dict]:
    return await _call(company_db.list_postings)


@router.post("/company/jobs", status_code=201)
async def post_job(job: NewJob) -> dict:
    return await _call(company_db.create_posting, job.title, job.skills, job.min_years,
                       city=job.city, mode=job.mode, description=job.description)


@router.put("/company/jobs/{job_id}/min-years")
async def put_min_years(job_id: str, body: MinYears) -> dict:
    await _call(company_db.set_min_years, job_id, body.min_years)
    return {"job_id": job_id, "min_years": body.min_years}


@router.get("/company/jobs/{job_id}/candidates")
async def get_candidates(job_id: str, min_years: int | None = Query(None, ge=0, le=30),
                         must_have: list[str] = Query(default_factory=list)) -> list[dict]:
    return await _call(company_db.rank_candidates, job_id, min_years, must_have)


@router.post("/company/jobs/{job_id}/candidates/{talent_id}/status")
async def post_status(job_id: str, talent_id: str, body: StatusChange) -> dict:
    status = await _call(company_db.change_status, job_id, talent_id, body.status, by="company")
    return {"job_id": job_id, "talent_id": talent_id, "status": status}


@router.post("/company/jobs/{job_id}/candidates/{talent_id}/schedule")
async def post_schedule(job_id: str, talent_id: str, body: Schedule) -> dict:
    when = await _call(company_db.schedule_interview, job_id, talent_id, body.interview_at)
    return {"job_id": job_id, "talent_id": talent_id, "status": "scheduled", "interview_at": when}


@router.post("/company/reset")
async def post_reset() -> dict:
    await _call(company_db.reset_demo)
    return {"status": "ok"}


@router.get("/candidate/{talent_id}/applications")
async def get_candidate_applications(talent_id: str) -> list[dict]:
    return await _call(company_db.talent_applications, talent_id)


@router.post("/candidate/{talent_id}/applications/{job_id}")
async def post_candidate_status(talent_id: str, job_id: str, body: StatusChange) -> dict:
    status = await _call(company_db.change_status, job_id, talent_id, body.status, by="candidate")
    return {"job_id": job_id, "talent_id": talent_id, "status": status}
