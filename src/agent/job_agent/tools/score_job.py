"""Tool: score_job — gives one job a match percentage, city, reason and the skill gaps.

The agent runs it on all jobs in parallel. The percentage is the teammate's ATS-style comparison
(requirements 55%, related experience 20%, level 10%, degree 5%, place 10%): deterministic and explainable,
so Claude does not change it. The reason is in Arabic (shown in the UI) and names the gaps.
"""
from __future__ import annotations

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from src.agent.job_agent.ats.matching import match_job
from src.agent.text.arabic import normalize_arabic, unique_strings
from src.logger import get_logger, log_step

from ._text import CITY_ALIASES, canonical_city

log = get_logger("job_agent.score_job")


class ScoreJobInput(BaseModel):
    """Parameters of score_job."""
    profile: dict = Field(description="Candidate profile from read_cv")
    job: dict = Field(description="One job from search_jobs (needs id, title, city, skills)")
    cv_text: str = Field(default="", description="Full CV text: job keywords are also looked up here, like an ATS")


def match_profile(profile: dict) -> dict:
    """The profile matching works on: the ATS reading when there is one, else the short profile."""
    ats = profile.get("ats_profile")
    base = dict(ats) if ats else {
        "skills": [], "languages": [], "jobTitles": [], "suggestedRoles": [], "searchKeywords": [], "experience": [],
        "education": [profile["major"]] if profile.get("major") else [], "yearsExperience": None, "ats": None,
    }
    base["skills"] = unique_strings([*base.get("skills", []), *profile.get("skills", [])])   # skills the candidate typed in count too
    if base.get("yearsExperience") is None:
        base["yearsExperience"] = profile.get("experience_years")
    city = canonical_city(profile.get("city"))
    if city:   # every spelling of the city, so «الرياض» and «Riyadh» job locations both match
        contact = dict((base.get("ats") or {}).get("contact") or {})
        contact["city"] = " ".join(normalize_arabic(alias) for alias in CITY_ALIASES.get(city, [city]))
        base["ats"] = {**(base.get("ats") or {}), "contact": contact}
    return base


def as_match_job(job: dict) -> dict:
    """A catalogue job (jobs.json or postings) in the shape matching expects."""
    arabic_title = job.get("title_ar")
    return {
        "title": arabic_title or job.get("title", ""),
        "english": job.get("english") or (job.get("title", "") if arabic_title else ""),
        "description": job.get("description_ar") or job.get("description") or "",
        "skills": list(job.get("skills") or []),
        "location": job.get("city") or "",
        "mode": job.get("mode") or "",
    }


@log_step(summary=lambda r: f"job={r['job_id']} match={r['match']}% gaps={len(r['missing_skills'])}")
def score_job(profile: dict, job: dict, cv_text: str = "") -> dict:
    """Return {"job_id", "match": 0-100, "city", "matched_skills", "missing_skills", "reason", "via": "ats"}."""
    result = match_job(match_profile(profile), as_match_job(job), cv_text)
    return {"job_id": job["id"], "match": result["score"], "city": job.get("city"), "matched_skills": result["matchedSkills"],
            "missing_skills": result["missingSkills"], "reason": result["reason"], "via": "ats"}


score_job_tool = StructuredTool.from_function(
    score_job, name="score_job", args_schema=ScoreJobInput,
    description="Score how well one job fits the candidate: match 0-100, city, the skill gaps and a short Arabic reason.")
