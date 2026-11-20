"""State carried through the Interview Agent graph.

The graph runs once per event (the recruiter speaks, the candidate signs, the candidate picks an
option, the interpreter button). A checkpointer keyed by session_id keeps the state between events.
Enums live in src/agent/schemas.py.
"""
from __future__ import annotations

from typing import TypedDict

from src.agent.schemas import EventType, Mode, Notice


class InterviewEvent(TypedDict, total=False):
    type: EventType
    text: str                      # question: recruiter's words from the browser (Web Speech API)
    audio: bytes                   # question: raw audio (server fallback)
    segments: list                 # signs: one keypoint sequence per sign
    index: int | None              # choose: 0..n-1, or None for "None of these"


class InterviewState(TypedDict, total=False):
    session_id: str
    mode: Mode                     # chosen by the candidate before the interview
    event: InterviewEvent          # the event being handled in this run
    last_question: str             # recruiter's last question (from speech_to_text)
    candidate_words: list[list[dict]]  # top words per sign (from recognize_sign)
    sentence_options: list[str]    # 3 options (from compose_sentence)
    chosen_sentence: str | None    # sent to the recruiter (this event only)
    none_count: int                # times the candidate picked "None of these"
    interpreter_called: bool
    interpreter: dict | None       # call_interpreter result (this event only)
    notice: Notice | None          # why an event was ignored (this event only)
