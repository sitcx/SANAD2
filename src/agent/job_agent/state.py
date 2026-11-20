"""State carried through the Job Agent graph."""
from __future__ import annotations

import operator
from typing import Annotated, TypedDict


class JobAgentState(TypedDict, total=False):
    cv_file: str               # path of the uploaded CV
    answers: dict              # candidate's answers to missing_info (e.g. {"city": "Riyadh"})
    profile: dict              # skills, major, experience, city (from read_cv + answers)
    missing_info: list[str]    # fields the agent must ask the candidate about
    widened: bool              # True when the search was widened
    jobs: list[dict]           # all jobs found by search_jobs
    scored_jobs: Annotated[list[dict], operator.add]  # filled in parallel by score_job
    recommended: list[dict]    # top jobs shown as "recommended"


class ScoreTask(TypedDict):
    """Input of one parallel score_job branch."""
    profile: dict
    job: dict
