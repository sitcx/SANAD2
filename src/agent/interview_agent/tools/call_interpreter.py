"""Tool: call_interpreter — brings a human sign-language interpreter into the call.

Hackathon: shows "connecting to an interpreter..." then "interpreter joined".
A real deployment would page an interpreter service here.
"""
from __future__ import annotations

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from src.agent.schemas import InterpreterReason
from src.logger import log_step


class CallInterpreterInput(BaseModel):
    """Parameters of call_interpreter."""
    session_id: str = Field(description="Interview session id")
    reason: InterpreterReason = Field(
        description='"button" = candidate pressed "I need an interpreter"; "none_limit" = too many "None of these"')


@log_step(summary=lambda r: f"session={r['session_id']} reason={r['reason']} -> interpreter joined")
def call_interpreter(session_id: str, reason: InterpreterReason | str) -> dict:
    """reason = "button" (manual) or "none_limit" (forced)."""
    reason = InterpreterReason(reason)   # raises ValueError for an unknown reason
    return {
        "session_id": session_id,
        "reason": reason.value,
        "steps": [
            {"status": "connecting", "message_ar": "جارٍ الاتصال بمترجم لغة الإشارة..."},
            {"status": "joined", "message_ar": "انضم مترجم لغة الإشارة إلى المقابلة."},
        ],
    }


call_interpreter_tool = StructuredTool.from_function(
    call_interpreter, name="call_interpreter", args_schema=CallInterpreterInput,
    description="Bring a human sign-language interpreter into the interview.")
