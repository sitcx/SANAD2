"""Speech-to-text fallback on the server.

The main path is the browser's Web Speech API (ar-SA), which sends text only.
This module is the server-side fallback if audio is sent instead. It uses
faster-whisper when installed (pip install faster-whisper); it is optional.
"""
from __future__ import annotations

import io
from functools import lru_cache

from src.agent.core.config import get_config
from src.logger import log_step


@lru_cache(maxsize=1)
def _whisper():
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError("server speech-to-text needs `pip install faster-whisper`; "
                           "the browser should send text instead") from exc
    size = get_config().get("speech", {}).get("whisper_model", "small")
    return WhisperModel(size, device="cpu", compute_type="int8")


@log_step(summary=lambda text: f"{len(text.split())} words")
def transcribe(audio_bytes: bytes, language: str = "ar") -> str:
    """Return the Arabic transcript of the audio."""
    segments, _info = _whisper().transcribe(io.BytesIO(audio_bytes), language=language)
    return " ".join(segment.text.strip() for segment in segments).strip()
