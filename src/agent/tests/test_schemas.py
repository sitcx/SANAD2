"""schemas.py: validated Claude responses and WebSocket messages."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from src.agent.api import app
from src.agent.inference import llm
from src.agent.interview_agent.tools.compose_sentence import compose_sentence
from src.agent.job_agent.tools.read_cv import read_cv
from src.agent.job_agent.tools.score_job import score_job
from src.agent.job_agent.tools.search_jobs import load_jobs
from src.agent.schemas import (CvProfileResponse, JobScoreResponse, Mode, SentenceOptionsResponse,
                               event_message_adapter)


class FakeClaude:
    """Stands in for ChatAnthropic: returns a canned reply for each schema, or raises."""

    def __init__(self, replies):
        self.replies = replies
        self.prompts: list[str] = []

    def with_structured_output(self, schema, method=None):
        assert method == "json_schema", "claude-sonnet-5-5 needs native structured output"
        fake = self

        class Runner:
            def invoke(self, prompt):
                fake.prompts.append(prompt)
                reply = fake.replies[schema]
                if isinstance(reply, Exception):
                    raise reply
                return reply
        return Runner()


@pytest.fixture
def claude(monkeypatch):
    def install(replies):
        fake = FakeClaude(replies)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        monkeypatch.setattr(llm, "get_llm", lambda: fake)
        return fake
    return install


# ---------------------------------------------------------------- Claude responses

def test_read_cv_uses_validated_claude_reply(claude, tmp_path):
    claude({CvProfileResponse: CvProfileResponse(skills=["SQL"], city="Riyadh", experience_years=4)})
    cv = tmp_path / "cv.txt"
    cv.write_text("any text", encoding="utf-8")
    assert read_cv(str(cv)) == {"skills": ["SQL"], "major": None, "experience_years": 4.0, "city": "Riyadh"}


def test_dict_reply_is_validated_too(claude):
    claude({JobScoreResponse: {"match": 88, "reason": "مناسبة لمهاراتك"}})
    job = load_jobs()[0]
    result = score_job({"skills": ["Excel"], "city": "Riyadh"}, job)
    assert (result["match"], result["reason"], result["via"]) == (88, "مناسبة لمهاراتك", "llm")


def test_invalid_claude_reply_falls_back_to_rules(claude):
    claude({JobScoreResponse: {"match": 150, "reason": "x"}})        # match > 100, reason too short
    result = score_job({"skills": ["Excel"], "city": "Riyadh"}, load_jobs()[0])
    assert result["via"] == "rules" and 0 <= result["match"] <= 100


def test_claude_error_falls_back_to_templates(claude):
    claude({SentenceOptionsResponse: TimeoutError("network")})
    words = [[{"label_ar": "أنا", "score": 0.9}], [{"label_ar": "خبرة", "score": 0.8}]]
    assert compose_sentence(words, "سؤال") == ["أنا خبرة"]


def test_compose_sentence_with_claude(claude):
    fake = claude({SentenceOptionsResponse: SentenceOptionsResponse(options=["أ", "ب", "ج", "د"])})
    words = [[{"label_ar": "خبرة", "score": 0.9}]]
    assert compose_sentence(words, "حدثنا عن خبرتك") == ["أ", "ب", "ج"]   # cut to sentence_options
    assert "حدثنا عن خبرتك" in fake.prompts[0]


def test_response_models_reject_bad_values():
    with pytest.raises(ValidationError):
        JobScoreResponse(match=-1, reason="سبب")
    with pytest.raises(ValidationError):
        SentenceOptionsResponse(options=[])
    with pytest.raises(ValidationError):
        CvProfileResponse(experience_years=200)


# ---------------------------------------------------------------- WebSocket messages

@pytest.mark.parametrize("raw", [
    {"type": "question", "text": "سؤال"},
    {"type": "signs", "segments": [[[[0.1, 0.2], [0.3, 0.4]]]]},
    {"type": "choose", "index": 0},
    {"type": "choose", "index": None},
    {"type": "interpreter"},
])
def test_valid_messages(raw):
    assert event_message_adapter.validate_python(raw).type == raw["type"]


@pytest.mark.parametrize("raw", [
    {"type": "dance"},                                   # unknown type
    {"type": "question"},                                # no text or audio
    {"type": "question", "text": "   "},
    {"type": "signs", "segments": []},                   # no signs
    {"type": "signs", "segments": [[[[0.1]]]]},          # a point needs x and y
    {"type": "choose", "index": -1},
    {"type": "choose"},                                  # index is required (null = None of these)
    {"type": "interpreter", "extra": 1},                 # unknown field
])
def test_invalid_messages(raw):
    with pytest.raises(ValidationError):
        event_message_adapter.validate_python(raw)


def test_websocket_rejects_bad_messages_and_keeps_going(isolated):
    with TestClient(app) as client, client.websocket_connect("/interview/xyz") as ws:
        ws.send_json({"type": "start", "mode": "ai"})
        assert ws.receive_json()["mode"] == Mode.AI
        ws.send_json({"type": "choose", "index": "first"})
        error = ws.receive_json()
        assert error["type"] == "error" and error["error"] == "invalid_message" and error["details"]
        ws.send_json({"type": "question", "text": "ما خبرتك؟"})    # the interview continues
        state = ws.receive_json()
        assert state["type"] == "state" and state["last_question"] == "ما خبرتك؟"


def test_websocket_rejects_bad_start(isolated):
    with TestClient(app) as client, client.websocket_connect("/interview/bad") as ws:
        ws.send_json({"type": "start", "mode": "robot"})
        error = ws.receive_json()
        assert error["error"] == "invalid_message"
