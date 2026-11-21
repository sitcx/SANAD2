"""Server-side speech-to-text (kept for existing imports).

The implementation lives in src/agent/speech/speech.py: Whisper Large-v3, Arabic only.
The browser records the recruiter's microphone and sends the audio on WS /interview/{session}
as {"type": "question", "audio_b64": ...}; the Interview Agent's speech_to_text tool calls transcribe().
"""
from __future__ import annotations

from src.agent.speech.speech import ARABIC_LANGUAGE, SpeechError, transcribe

__all__ = ["ARABIC_LANGUAGE", "SpeechError", "transcribe"]
