"""Tool: recognize_sign — the candidate's signs as the most likely words.

Uses inference.sign_model.match_sign on keypoints sent from the browser (MediaPipe).
Each segment is one sign: a list of frames, each a list of [x, y(, z)] points.
"""
from __future__ import annotations

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from src.agent.inference.sign_model import load_gallery, match_sign
from src.logger import get_logger, log_step

log = get_logger("interview_agent.recognize_sign")


class RecognizeSignInput(BaseModel):
    """Parameters of recognize_sign."""
    keypoint_segments: list = Field(
        description="One item per sign: frames x points x [x, y] (42 points = left hand 21 + right hand 21)")
    top_k: int = Field(default=5, description="How many candidate words to return per sign")


def _summary(words: list[list[dict]]) -> str:
    best = [w[0]["label_ar"] if w else "?" for w in words]
    return f"{len(words)} signs, best words: {' | '.join(best)}"


@log_step(summary=_summary)
def recognize_sign(keypoint_segments: list, top_k: int = 5) -> list[list[dict]]:
    """Return, for each sign, the top words with scores (an empty list if a sign is unreadable)."""
    gallery_size = len(load_gallery())
    log.info("[INPUT] %d sign segments, gallery has %d words", len(keypoint_segments or []), gallery_size)
    if gallery_size == 0:
        log.warning("[WARN] sign gallery is empty -> no words (run inference/build_gallery.py)")
    words = []
    for i, segment in enumerate(keypoint_segments or [], start=1):
        try:
            words.append(match_sign(segment, top_k=top_k))
        except ValueError as exc:
            log.warning("[WARN] sign %d skipped: %s", i, exc)
            words.append([])
    return words


recognize_sign_tool = StructuredTool.from_function(
    recognize_sign, name="recognize_sign", args_schema=RecognizeSignInput,
    description="Match the candidate's hand keypoints to the most likely Saudi Sign Language words.")
