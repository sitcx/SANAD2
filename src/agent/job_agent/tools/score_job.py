"""Tool: score_job — gives one job a match percentage, city and reason.

The agent runs it on all jobs in parallel. The reason is in Arabic (shown in the UI).
"""
from __future__ import annotations

import json

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from src.agent.inference.llm import ask_claude, llm_available
from src.agent.schemas import JobScoreResponse
from src.logger import get_logger, log_step

from ._text import canonical_city
from .search_jobs import skill_overlap

log = get_logger("job_agent.score_job")


class ScoreJobInput(BaseModel):
    """Parameters of score_job."""
    profile: dict = Field(description="Candidate profile from read_cv")
    job: dict = Field(description="One job from search_jobs (needs id, title, city, skills)")


_PROMPT = """You match a deaf or hard-of-hearing job seeker to a job.
Candidate profile: {profile}
Job: {job}
Rule-based estimate: {estimate}%

Give a match percentage and one short reason in simple Arabic.
Base the match on skills, experience and city. Never consider disability against the candidate."""


def rule_score(profile: dict, job: dict) -> tuple[int, list[str]]:
    """70% skills covered + 20% same city/remote + 10% experience (3+ years = full)."""
    shared = skill_overlap(profile, job)
    required = job.get("skills") or []
    skill_part = len(shared) / len(required) if required else 0.5
    job_city = canonical_city(job.get("city"))
    city = canonical_city(profile.get("city"))
    city_part = 1.0 if job_city == "remote" or (city and city == job_city) else 0.3
    years = profile.get("experience_years") or 0
    exp_part = min(years / 3, 1.0)
    score = round(100 * (0.7 * skill_part + 0.2 * city_part + 0.1 * exp_part))
    return max(0, min(100, score)), shared


def _rule_reason(shared: list[str], job: dict) -> str:
    title = job.get("title_ar") or job.get("title", "")
    skills = job.get("skills_ar") or {}
    if shared:
        return f"مهاراتك في {'، '.join(skills.get(s, s) for s in shared)} تناسب متطلبات وظيفة {title}."
    return f"وظيفة {title} قريبة من مجالك ويمكنك تطوير مهاراتها."


@log_step(summary=lambda r: f"job={r['job_id']} match={r['match']}% via={r['via']}")
def score_job(profile: dict, job: dict) -> dict:
    """Return {"job_id": ..., "match": 0-100, "city": ..., "reason": ..., "via": "llm"|"rules"}."""
    estimate, shared = rule_score(profile, job)
    result = {"job_id": job["id"], "match": estimate, "city": job.get("city"),
              "matched_skills": shared, "reason": _rule_reason(shared, job), "via": "rules"}
    if llm_available():
        try:
            prompt = _PROMPT.format(profile=json.dumps(profile, ensure_ascii=False),
                                    job=json.dumps(job, ensure_ascii=False), estimate=estimate)
            reply = ask_claude(prompt, JobScoreResponse)
            result["match"] = reply.match
            result["reason"] = reply.reason.strip()
            result["via"] = "llm"
        except Exception as exc:  # noqa: BLE001 - keep the rule-based score
            log.warning("[FALLBACK] Claude failed for %s (%s) -> rule score", job["id"], type(exc).__name__)
    else:
        log.info("[FALLBACK] no ANTHROPIC_API_KEY -> rule score")
    return result


score_job_tool = StructuredTool.from_function(
    score_job, name="score_job", args_schema=ScoreJobInput,
    description="Score how well one job fits the candidate: match 0-100, city and a short Arabic reason.")
