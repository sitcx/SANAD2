from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.agent.interview_agent.tools import TOOLS as INTERVIEW_TOOLS
from src.agent.job_agent.tools import TOOLS as JOB_TOOLS

EXPECTED_REQUIRED = {
    "read_cv": ["cv_file"],
    "search_jobs": ["profile"],
    "score_job": ["profile", "job"],
    "speech_to_text": ["text_or_audio"],
    "recognize_sign": ["keypoint_segments"],
    "compose_sentence": ["candidate_words", "last_question"],
    "call_interpreter": ["session_id", "reason"],
}


def test_every_tool_declares_parameters():
    tools = {t.name: t for t in JOB_TOOLS + INTERVIEW_TOOLS}
    assert set(tools) == set(EXPECTED_REQUIRED)
    for name, required in EXPECTED_REQUIRED.items():
        schema = tools[name].args_schema.model_json_schema()
        assert schema["required"] == required, name
        assert all(prop.get("description") for prop in schema["properties"].values()), name


def test_call_interpreter_reason_is_restricted():
    tool = next(t for t in INTERVIEW_TOOLS if t.name == "call_interpreter")
    assert tool.invoke({"session_id": "x", "reason": "button"})["reason"] == "button"
    schema = tool.args_schema.model_json_schema()
    ref = schema["properties"]["reason"]["$ref"].split("/")[-1]      # enum lives in $defs
    assert schema["$defs"][ref]["enum"] == ["button", "none_limit"]
    with pytest.raises(ValidationError):
        tool.invoke({"session_id": "x", "reason": "because"})
