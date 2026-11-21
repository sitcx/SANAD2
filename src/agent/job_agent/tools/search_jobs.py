"""Tool: search_jobs — finds jobs related to the candidate's profile.

Reads jobs from job_agent.jobs_file and the postings table (company jobs + jobs found by the search agent). If too few match, the agent calls it again
with widen=True (nearby cities / related roles).
"""
from __future__ import annotations

import json

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from src.agent.core.config import get_config, project_path
from src.logger import get_logger, log_step

from src.agent.job_agent.ats.matching import skills_match

from ._text import NEARBY_CITIES, canonical_city, canonical_skill

log = get_logger("job_agent.search_jobs")


class SearchJobsInput(BaseModel):
    """Parameters of search_jobs."""
    profile: dict = Field(description="Candidate profile from read_cv: skills, major, experience_years, city")
    widen: bool = Field(default=False, description="True = also nearby cities and jobs without a shared skill")


def load_jobs() -> list[dict]:
    path = project_path(get_config()["job_agent"]["jobs_file"])
    return json.loads(path.read_text(encoding="utf-8"))


def catalogue() -> list[dict]:
    """Every job the agent can recommend: jobs.json plus the active postings in the database (the company's jobs
    and the jobs found by the search agent). A posting with the same id replaces the jobs.json entry."""
    from src.database.candidate_db import active_postings

    by_id = {job["id"]: job for job in load_jobs()}
    for posting in active_postings():
        by_id[posting["id"]] = {**by_id.get(posting["id"], {}), **posting}
    return list(by_id.values())


def _candidate_skills(profile: dict) -> list[str]:
    return [*profile.get("skills", []), *((profile.get("ats_profile") or {}).get("skills", []))]


def skill_overlap(profile: dict, job: dict) -> list[str]:
    """Required skills the candidate has, in any language or spelling («اكسل» = «Excel», «Zendesk» counts as CRM)."""
    mine = _candidate_skills(profile)
    canonical = {canonical_skill(s) for s in mine}
    return [s for s in job.get("skills", []) if canonical_skill(s) in canonical or any(skills_match(m, s) for m in mine)]


def _city_ok(job: dict, city: str | None, widen: bool) -> bool:
    job_city = canonical_city(job.get("city"))
    if job_city == "remote" or str(job.get("mode", "")).lower() == "remote":
        return True
    if city is None:
        return widen
    allowed = NEARBY_CITIES.get(city, {city}) if widen else {city}
    return job_city in allowed


@log_step(summary=lambda jobs: f"{len(jobs)} jobs: {[j['id'] for j in jobs]}")
def search_jobs(profile: dict, widen: bool = False) -> list[dict]:
    """Return the list of related jobs.

    Normal: jobs in the candidate's city (or remote) sharing at least one skill.
    Widened: any job sharing a skill (any city), plus nearby/remote jobs without a shared skill.
    """
    city = canonical_city(profile.get("city"))
    all_jobs = catalogue()
    log.info("[INPUT] %d jobs in catalogue, city=%s, widen=%s", len(all_jobs), city or "none", widen)
    found = []
    for job in all_jobs:
        shares_skill = bool(skill_overlap(profile, job))
        keep = (shares_skill or _city_ok(job, city, widen=True)) if widen \
            else (shares_skill and _city_ok(job, city, widen=False))
        if keep:
            found.append(job)
    return found


search_jobs_tool = StructuredTool.from_function(
    search_jobs, name="search_jobs", args_schema=SearchJobsInput,
    description="Find jobs that match the candidate's skills and city; widen=True searches more broadly.")
