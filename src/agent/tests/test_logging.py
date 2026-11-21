"""Guards that every operation writes to the log, so a missing log line is a failing test."""
from __future__ import annotations

import logging

import pytest

from src.agent.inference import sign_model, speech
from src.agent.interview_agent import tools as interview_tools
from src.agent.interview_agent.graph import InterviewSession, build_interview_graph
from src.agent.job_agent import tools as job_tools
from src.agent.job_agent.graph import recommend_jobs
from src.database import db

from .test_interview_agent import _signs

# Every operation that must log [START] / [OK] / [FAIL]. Add new tools and db functions here.
LOGGED_FUNCTIONS = [
    job_tools.read_cv, job_tools.search_jobs, job_tools.score_job,
    interview_tools.speech_to_text, interview_tools.recognize_sign,
    interview_tools.compose_sentence, interview_tools.call_interpreter,
    sign_model.match_sign, speech.transcribe,
    db.init_db, db.save_candidate, db.list_jobs, db.start_interview, db.update_interview, db.get_interview,
]


class _Collect(logging.Handler):
    def __init__(self):
        super().__init__()
        self.lines: list[str] = []

    def emit(self, record):
        self.lines.append(f"{record.name} {record.getMessage()}")


@pytest.fixture
def log_lines():
    handler = _Collect()
    logger = logging.getLogger("sanad")
    logger.addHandler(handler)
    yield handler.lines
    logger.removeHandler(handler)


@pytest.mark.parametrize("fn", LOGGED_FUNCTIONS, ids=lambda f: f.__name__)
def test_function_is_wrapped_with_log_step(fn):
    assert hasattr(fn, "__wrapped__"), f"{fn.__name__} has no @log_step"


def _ok(lines, step):
    return any(f"[OK]    {step} " in line or line.endswith(f"[OK]    {step}") for line in lines)


def test_job_flow_logs_every_step(log_lines):
    profile = {"skills": ["Excel"], "city": "Riyadh"}
    recommend_jobs(profile=profile)
    db.init_db()
    db.save_candidate("x", profile)
    for step in ("search_jobs", "score_job", "init_db", "save_candidate"):
        assert _ok(log_lines, step), step
    text = "\n".join(log_lines)
    for tag in ("[RUN] Job Agent", "[DECISION]", "[RESULT]", "[DONE] Job Agent"):   # scoring is deterministic: no LLM fallback
        assert tag in text, tag


def test_interview_flow_logs_every_step(gallery, log_lines):
    db.init_db()
    interview_id = db.start_interview(None, "analyst", "ai")
    s = InterviewSession("log-test", "ai", graph=build_interview_graph())
    s.send({"type": "question", "text": "عرّف بنفسك"})
    s.send({"type": "signs", "segments": _signs("open")})
    s.send({"type": "choose", "index": None})
    s.send({"type": "interpreter"})
    db.update_interview(interview_id, none_count=1)
    for step in ("speech_to_text", "recognize_sign", "match_sign", "compose_sentence",
                 "call_interpreter", "start_interview", "update_interview"):
        assert _ok(log_lines, step), step
    text = "\n".join(log_lines)
    for tag in ("[RUN] interview started", "[EVENT]", "[DECISION]", "None of these", "[DONE] event"):
        assert tag in text, tag


def test_failure_is_logged(log_lines):
    with pytest.raises(FileNotFoundError):
        job_tools.read_cv("does-not-exist.txt")
    assert any("[FAIL]  read_cv" in line and "FileNotFoundError" in line for line in log_lines)
