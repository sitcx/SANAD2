"""OpenRouter speech-to-text: Whisper Large-v3 in the cloud, used for live Arabic captions.

POST https://openrouter.ai/api/v1/audio/transcriptions with base64 audio (JSON body).
The key is read on the server from .env (OPENROUTER_API_KEY) and is never logged or sent to the browser.

Arabic only:
    - The request leaves `language` unset so Whisper reports the spoken language (verbose_json).
      Forcing "ar" would turn English speech into an invented Arabic paraphrase that cannot be detected
      (seen in testing). The text is accepted only when the spoken language is Arabic; anything else
      raises NonArabicSpeech. Whisper's "translate" task is never used.
    - The text must also pass speech.ensure_arabic (Arabic-script check) and known silence
      hallucinations are dropped.
    - provider.zdr = true: only providers that do not retain the audio may handle it.

OpenRouter has no streaming transcription API: each call takes a complete clip. src/agent/speech/live.py
gets live captions by re-transcribing the sentence in progress about once a second.
"""
from __future__ import annotations

import base64
import io
import time
import wave
from dataclasses import dataclass
from typing import Any

import httpx

from src.agent.core.config import get_config, get_secret
from src.logger import get_logger

from .speech import ARABIC_LANGUAGE, NonArabicSpeech, SpeechError, _clean, ensure_arabic

log = get_logger("speech.openrouter")

OPENROUTER_URL = "https://openrouter.ai/api/v1/audio/transcriptions"
SAMPLE_RATE = 16_000
_ARABIC_NAMES = {ARABIC_LANGUAGE, "arabic"}
_DEFAULTS: dict[str, Any] = {
    "openrouter_model": "openai/whisper-large-v3",
    "zero_data_retention": True,
    "request_timeout_s": 30,
}


class SpeechNotConfigured(SpeechError):
    code = "speech_not_configured"
    message = "الترجمة المباشرة غير مفعّلة على الخادم: مفتاح OpenRouter غير موجود في ملف ‎.env."


class SpeechServiceUnavailable(SpeechError):
    code = "speech_service_unavailable"
    message = "خدمة الترجمة المباشرة غير متاحة حاليًا. تحقق من اتصال الخادم بالإنترنت ثم تحدّث مجددًا."


_HTTP_MESSAGES = {
    401: "مفتاح OpenRouter غير صالح. حدّث OPENROUTER_API_KEY في ملف ‎.env ثم أعد تشغيل سند.",
    402: "رصيد OpenRouter غير كافٍ لتشغيل الترجمة المباشرة. أضف رصيدًا ثم حاول مجددًا.",
    429: "طلبات الترجمة كثيرة الآن. انتظر لحظة ثم تحدّث مجددًا.",
}


def live_settings() -> dict[str, Any]:
    """config.yaml -> speech.live, with defaults."""
    return {**_DEFAULTS, **((get_config().get("speech") or {}).get("live") or {})}


def api_key() -> str:
    key = (get_secret("OPENROUTER_API_KEY") or "").strip()
    if not key:
        raise SpeechNotConfigured(detail="OPENROUTER_API_KEY is not set")
    return key


def pcm16_to_wav(pcm: bytes, sample_rate: int = SAMPLE_RATE) -> bytes:
    """Raw 16-bit little-endian mono PCM -> WAV file bytes."""
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(pcm)
    return buffer.getvalue()


@dataclass
class Transcript:
    text: str
    language: str | None
    seconds: float


async def transcribe_pcm(client: httpx.AsyncClient, pcm: bytes, *, final: bool) -> Transcript:
    """Transcribe one clip of 16 kHz mono PCM. Raises SpeechError (Arabic message) on failure.

    final=False (a partial caption): the text is returned even if it is short or mixed, but still only
    when the spoken language is Arabic. final=True: the full Arabic checks apply.
    """
    s = live_settings()
    body: dict[str, Any] = {
        "model": s["openrouter_model"],
        "temperature": 0,
        "response_format": "verbose_json",   # returns the spoken language
        "input_audio": {"data": base64.b64encode(pcm16_to_wav(pcm)).decode("ascii"), "format": "wav"},
    }
    if s["zero_data_retention"]:
        body["provider"] = {"zdr": True}
    started = time.perf_counter()
    try:
        response = await client.post(OPENROUTER_URL, json=body, timeout=float(s["request_timeout_s"]),
                                      headers={"Authorization": f"Bearer {api_key()}"})
    except httpx.HTTPError as exc:
        raise SpeechServiceUnavailable(detail=f"{type(exc).__name__}") from exc
    if response.status_code != 200:
        detail = f"HTTP {response.status_code}"
        try:
            detail += f": {str(response.json().get('error', {}).get('message', ''))[:160]}"
        except ValueError:
            pass
        message = _HTTP_MESSAGES.get(response.status_code)
        raise SpeechServiceUnavailable(message, detail=detail)
    data = response.json()
    language = (data.get("language") or "").strip().lower() or None
    text = _clean(str(data.get("text") or ""))
    seconds = len(pcm) / 2 / SAMPLE_RATE
    log.info("[RESULT] %s %.1f s audio -> language=%s, %d chars in %.1f s", "final" if final else "partial",
             seconds, language, len(text), time.perf_counter() - started)
    if language is not None and language not in _ARABIC_NAMES:
        raise NonArabicSpeech(detail=f"spoken language {language}")
    if final and text:
        text = ensure_arabic(text)
    return Transcript(text=text, language=language, seconds=seconds)
