from __future__ import annotations

from src.agent.inference.sign_model import match_sign
from src.agent.interview_agent.graph import InterviewSession, build_interview_graph

from .conftest import hand_shape


def _signs(*kinds):
    # Different position/size than the gallery: normalisation must remove that.
    return [(hand_shape(k, frames=15) * 0.35 + 0.1).tolist() for k in kinds]


def test_match_sign_finds_closest(gallery):
    for kind, word in (("open", "أنا"), ("fist", "خبرة"), ("wave", "بيانات")):
        top = match_sign(_signs(kind)[0], top_k=3)
        assert top[0]["label_ar"] == word
        assert top[0]["score"] >= top[-1]["score"]


def test_ai_mode_question_signs_choose(gallery):
    s = InterviewSession("s1", "ai", graph=build_interview_graph())
    out = s.send({"type": "question", "text": "  حدثنا   عن خبرتك "})
    assert out["last_question"] == "حدثنا عن خبرتك"

    out = s.send({"type": "signs", "segments": _signs("open", "fist", "wave")})
    assert len(out["sentence_options"]) == 3
    assert out["sentence_options"][0] == "أنا خبرة بيانات"

    out = s.send({"type": "choose", "index": 0})
    assert out["chosen_sentence"] == "أنا خبرة بيانات"
    assert out["sentence_options"] == []

    out = s.send({"type": "question", "text": "سؤال ثان"})
    assert out["chosen_sentence"] is None                 # per-event output cleared


def test_question_and_signs_together_use_new_question(gallery, monkeypatch):
    seen = {}

    def fake_compose(words, question):
        seen["question"] = question
        return ["a", "b", "c"]

    monkeypatch.setattr("src.agent.interview_agent.graph.compose_sentence", fake_compose)
    s = InterviewSession("s2", "ai", graph=build_interview_graph())
    s.send({"type": "question", "text": "سؤال جديد", "segments": _signs("open")})
    assert seen["question"] == "سؤال جديد"


def test_none_limit_forces_interpreter(gallery, isolated):
    isolated["interview_agent"]["max_none_of_these"] = 3
    s = InterviewSession("s3", "ai", graph=build_interview_graph())
    for expected in (1, 2):
        s.send({"type": "signs", "segments": _signs("open")})
        out = s.send({"type": "choose", "index": None})
        assert out["none_count"] == expected and not out["interpreter_called"]
    s.send({"type": "signs", "segments": _signs("fist")})
    out = s.send({"type": "choose", "index": None})
    assert out["interpreter_called"] and out["mode"] == "human"
    assert out["interpreter"]["reason"] == "none_limit"

    out = s.send({"type": "signs", "segments": _signs("open")})   # Case 1 now
    assert out["notice"] == "human_mode"


def test_consecutive_counter_resets(gallery, isolated):
    isolated["interview_agent"]["none_counter"] = "consecutive"
    s = InterviewSession("s4", "ai", graph=build_interview_graph())
    s.send({"type": "signs", "segments": _signs("open")})
    assert s.send({"type": "choose", "index": None})["none_count"] == 1
    s.send({"type": "signs", "segments": _signs("open")})
    assert s.send({"type": "choose", "index": 0})["none_count"] == 0


def test_interpreter_button_once(isolated):
    s = InterviewSession("s5", "ai", graph=build_interview_graph())
    out = s.send({"type": "interpreter"})
    assert out["interpreter"]["reason"] == "button" and out["mode"] == "human"
    assert s.send({"type": "interpreter"})["notice"] == "interpreter_already_called"


def test_empty_gallery_gives_no_options(isolated):
    s = InterviewSession("s6", "ai", graph=build_interview_graph())
    out = s.send({"type": "signs", "segments": _signs("open")})
    assert out["sentence_options"] == [] and out["notice"] == "no_signs_recognized"
