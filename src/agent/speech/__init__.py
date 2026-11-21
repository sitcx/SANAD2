"""Arabic-only speech-to-text (Whisper Large-v3). See speech.py."""
from .speech import (
    ARABIC_LANGUAGE,
    TASK,
    InvalidAudio,
    NoSpeechDetected,
    NonArabicSpeech,
    SpeechError,
    SpeechModelUnavailable,
    model_status,
    transcribe,
    warm_up,
)

__all__ = [
    "ARABIC_LANGUAGE", "TASK", "InvalidAudio", "NoSpeechDetected", "NonArabicSpeech", "SpeechError",
    "SpeechModelUnavailable", "model_status", "transcribe", "warm_up",
]
