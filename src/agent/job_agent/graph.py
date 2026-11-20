"""Job Agent graph.

Flow (sequential steps; scoring runs in parallel):
    read_cv -> [missing info? ask candidate] -> search_jobs
            -> [fewer than job_agent.min_matches? widen search] -> score_job (all jobs in parallel)
            -> rank -> all jobs + recommended jobs with match %, city and reason
"""
from __future__ import annotations

import time

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from src.agent.core.config import get_config
from src.logger import get_logger

from .state import JobAgentState, ScoreTask
from .tools.read_cv import missing_fields, read_cv
from .tools.score_job import score_job
from .tools.search_jobs import search_jobs

log = get_logger("job_agent")


def _settings() -> dict:
    return get_config()["job_agent"]


def read_cv_node(state: JobAgentState) -> dict:
    profile = dict(state["profile"]) if state.get("profile") else read_cv(state["cv_file"])
    for key, value in (state.get("answers") or {}).items():
        if value not in (None, "", []):
            profile[key] = value
    if state.get("answers"):
        log.info("[INPUT] candidate answered: %s", sorted(state["answers"]))
    missing = missing_fields(profile)
    if missing:
        log.info("[DECISION] missing %s -> stop and ask the candidate", missing)
    else:
        log.info("[DECISION] profile complete -> search jobs")
    return {"profile": profile, "missing_info": missing}


def after_read_cv(state: JobAgentState) -> str:
    return "ask_candidate" if state.get("missing_info") else "search_jobs"


def search_node(state: JobAgentState) -> dict:
    return {"jobs": search_jobs(state["profile"]), "widened": False}


def after_search(state: JobAgentState):
    found, minimum = len(state.get("jobs", [])), _settings()["min_matches"]
    if found < minimum and not state.get("widened"):
        log.info("[DECISION] %d jobs < min_matches %d -> widen search", found, minimum)
        return "widen_search"
    log.info("[DECISION] %d jobs >= min_matches %d -> score", found, minimum)
    return _fan_out(state)


def widen_node(state: JobAgentState) -> dict:
    return {"jobs": search_jobs(state["profile"], widen=True), "widened": True}


def _fan_out(state: JobAgentState):
    jobs = state.get("jobs", [])
    if not jobs:
        log.info("[DECISION] no jobs found -> nothing to score")
        return "rank"
    log.info("[DECISION] scoring %d jobs in parallel", len(jobs))
    return [Send("score_job", {"profile": state["profile"], "job": job}) for job in jobs]


def score_node(task: ScoreTask) -> dict:
    return {"scored_jobs": [score_job(task["profile"], task["job"])]}


def rank_node(state: JobAgentState) -> dict:
    by_id = {job["id"]: job for job in state.get("jobs", [])}
    ranked = sorted(state.get("scored_jobs", []), key=lambda s: s["match"], reverse=True)
    merged = [{**by_id.get(s["job_id"], {}), **s} for s in ranked]
    recommended = merged[: _settings()["recommended_jobs"]]
    log.info("[RESULT] ranked %d jobs; recommended: %s", len(merged),
             ", ".join(f"{j['job_id']} {j['match']}%" for j in recommended) or "none")
    return {"jobs": merged, "recommended": recommended}


def build_job_graph():
    """Build and compile the LangGraph StateGraph for the Job Agent."""
    graph = StateGraph(JobAgentState)
    graph.add_node("read_cv", read_cv_node)
    graph.add_node("search_jobs", search_node)
    graph.add_node("widen_search", widen_node)
    graph.add_node("score_job", score_node)
    graph.add_node("rank", rank_node)

    graph.add_edge(START, "read_cv")
    graph.add_conditional_edges("read_cv", after_read_cv, {"ask_candidate": END, "search_jobs": "search_jobs"})
    graph.add_conditional_edges("search_jobs", after_search, ["widen_search", "score_job", "rank"])
    graph.add_conditional_edges("widen_search", _fan_out, ["score_job", "rank"])
    graph.add_edge("score_job", "rank")
    graph.add_edge("rank", END)
    return graph.compile()


def recommend_jobs(cv_file: str | None = None, answers: dict | None = None, profile: dict | None = None) -> dict:
    """Run the Job Agent once. Returns the final state (check "missing_info" first)."""
    state: JobAgentState = {"answers": answers or {}}
    if profile:
        state["profile"] = profile
    elif cv_file:
        state["cv_file"] = cv_file
    else:
        raise ValueError("cv_file or profile is required")
    log.info("[RUN] Job Agent started (%s)", "profile given" if profile else "from CV file")
    started = time.perf_counter()
    try:
        result = build_job_graph().invoke(state)
    except Exception as exc:
        log.error("[FAIL]  Job Agent stopped -> %s: %s", type(exc).__name__, exc)
        raise
    outcome = "needs info" if result.get("missing_info") else f"{len(result.get('recommended', []))} recommended"
    log.info("[DONE] Job Agent finished in %.0f ms -> %s", (time.perf_counter() - started) * 1000, outcome)
    return result
