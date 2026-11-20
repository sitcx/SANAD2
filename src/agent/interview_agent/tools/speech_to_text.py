"""Tool: speech_to_text — the recruiter's speech as Arabic text for the candidate.

Main path: the browser (Web Speech API) sends the text; fallback: inference.speech.
"""
from __future__ import annotations

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from src.agent.inference.speech import transcribe
from src.logger import get_logger, log_step

log = get_logger("interview_agent.speech_to_text")


class SpeechToTextInput(BaseModel):
    """Parameters of speech_to_text."""
    text_or_audio: str | bytes = Field(
        description="Recruiter's words as text (from the browser), or raw audio bytes (server fallback)")


@log_step(summary=lambda q: f"question of {len(q.split())} words")
def speech_to_text(text_or_audio) -> str:
    """Return the recruiter's question as text (the graph stores it as last_question)."""
    if isinstance(text_or_audio, (bytes, bytearray)):
        log.info("[INPUT] audio, %d bytes -> server transcription", len(text_or_audio))
        return transcribe(bytes(text_or_audio))
    log.info("[INPUT] text from the browser")
    return " ".join(str(text_or_audio or "").split())


speech_to_text_tool = StructuredTool.from_function(
    speech_to_text, name="speech_to_text", args_schema=SpeechToTextInput,
    description="Turn the recruiter's speech (text or audio) into the Arabic question shown to the candidate.")
