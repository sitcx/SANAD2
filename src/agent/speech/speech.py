"""Arabic-only speech-to-text with Whisper Large-v3.

The recruiter's recorded speech (any container the browser produces: webm/opus, ogg, wav, mp4)
becomes Arabic text for the deaf candidate and for the Interview Agent (speech_to_text tool).

Arabic only, by design:
    - The decoding language is fixed to Arabic (ARABIC_LANGUAGE = "ar"); Whisper's automatic
      language detection is never used, so the model cannot switch to another output language.
    - The task is fixed to "transcribe" (TASK); Whisper's "translate" task (which outputs English)
      is never used.
    - Spoken-language gate: Whisper's language detector only *checks* the recording. If another
      language is detected with confidence (and Arabic is unlikely), the audio is rejected with
      NonArabicSpeech. Without this, Whisper forced to Arabic turns English speech into a made-up
      Arabic paraphrase. It never changes the output language.
    - The result must be written in Arabic script. Speech that comes out mostly in another script
      (e.g. an English sentence) is rejected with NonArabicSpeech instead of being shown.
      An Arabic sentence that contains a short foreign term (e.g. "Excel") is kept.
    - transcribe(..., language=...) raises ValueError for anything other than "ar".

Engine: faster-whisper (CTranslate2 build of openai/whisper-large-v3), loaded once and shared.
Settings: config.yaml -> speech (model, device, compute_type, beam_size, max_seconds, ...).
Install:  pip install faster-whisper   (the model, ~3 GB, downloads on first use)

Every failure is a SpeechError with a stable `code` and an Arabic `message` for the web UI.
"""
from __future__ import annotations

import io
import os
import re
import threading
import time
from typing import Any

import numpy as np

from src.agent.core.config import get_config
from src.logger import get_logger, log_step

log = get_logger("speech")

ARABIC_LANGUAGE = "ar"          # the only transcription language
TASK = "transcribe"             # never "translate" (Whisper's translate task outputs English)
SAMPLE_RATE = 16_000            # Whisper input rate

_DEFAULTS: dict[str, Any] = {
    "whisper_model": "large-v3",
    "device": "auto",            # auto = CUDA if it works, otherwise CPU
    "compute_type": "auto",      # auto = int8_float16 on CUDA, int8 on CPU
    "beam_size": 5,
    "max_seconds": 120,          # longer recordings are rejected
    "min_arabic_ratio": 0.5,     # share of words that must be written in Arabic script
    "reject_other_languages": True,   # spoken-language gate (see the module docstring)
    "other_language_min_prob": 0.5,   # reject when another language is at least this likely ...
    "arabic_max_prob_to_reject": 0.2,  # ... and Arabic is less likely than this
    "initial_prompt": "سؤال من مسؤول التوظيف في مقابلة عمل باللغة العربية.",
}

# Arabic, Arabic Supplement, Arabic Extended-A and the presentation forms.
_ARABIC_LETTER = re.compile(r"[ؠ-يٮ-ۓۺ-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿]")
_OTHER_LETTER = re.compile(r"[A-Za-zÀ-ɏͰ-ϿЀ-ӿ]")
# Phrases Whisper is known to invent on silence or noise in Arabic (subtitle credits, channel outros).
_HALLUCINATIONS = (
    "ترجمة نانسي قنقر", "اشتركوا في القناة", "اشترك في القناة", "شكرا للمشاهدة", "شكراً للمشاهدة",
    "شكرا على المشاهدة", "نهاية الحلقة", "سبحان الله وبحمده",
)


# ---------------------------------------------------------------- errors (code + Arabic message)

class SpeechError(RuntimeError):
    """A speech-to-text failure the web UI can explain to the user in Arabic."""
    code = "speech_error"
    message = "تعذّر تحويل الكلام إلى نص. حاول مرة أخرى."

    def __init__(self, message: str | None = None, detail: str = ""):
        if message:
            self.message = message
        self.detail = detail
        super().__init__(detail or self.code)


class SpeechModelUnavailable(SpeechError):
    code = "speech_model_unavailable"
    message = "خدمة تحويل الكلام العربي إلى نص غير متاحة على الخادم حاليًا. اكتب السؤال بدلًا من ذلك."


class InvalidAudio(SpeechError):
    code = "invalid_audio"
    message = "تعذّرت قراءة التسجيل الصوتي. سجّل السؤال مرة أخرى."


class NoSpeechDetected(SpeechError):
    code = "no_speech"
    message = "لم يُلتقط كلام واضح. اقترب من الميكروفون وتحدّث بالعربية ثم حاول مجددًا."


class NonArabicSpeech(SpeechError):
    code = "non_arabic_speech"
    message = "يتعرّف سند على الكلام العربي فقط. أعد السؤال باللغة العربية."


# ---------------------------------------------------------------- model

def settings() -> dict[str, Any]:
    """config.yaml -> speech, with defaults for missing keys."""
    return {**_DEFAULTS, **(get_config().get("speech") or {})}


_lock = threading.Lock()          # one load at a time; one transcription at a time (memory)
_model = None
_status: dict[str, Any] = {"state": "idle"}


def model_status() -> dict[str, Any]:
    """What the speech model is doing: idle | loading | ready | unavailable (+ device, error)."""
    s = settings()
    return {"model": s["whisper_model"], "language": ARABIC_LANGUAGE, "task": TASK, **_status}


def _device_plan(s: dict[str, Any]) -> list[tuple[str, str]]:
    """(device, compute_type) pairs to try, best first."""
    device, compute = str(s["device"]).lower(), str(s["compute_type"]).lower()
    devices = [device] if device in ("cpu", "cuda") else []
    if not devices:   # auto
        try:
            import ctranslate2
            devices = ["cuda", "cpu"] if ctranslate2.get_cuda_device_count() > 0 else ["cpu"]
        except Exception:  # noqa: BLE001 - no CUDA runtime: CPU
            devices = ["cpu"]
    default_compute = {"cuda": "int8_float16", "cpu": "int8"}
    return [(d, default_compute[d] if compute == "auto" else compute) for d in devices]


def _load():
    """Load Whisper Large-v3 once. Tries CUDA first (when auto) and falls back to CPU."""
    global _model
    if _model is not None:
        return _model
    with _lock:
        if _model is not None:
            return _model
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            _status.update(state="unavailable", error="faster-whisper is not installed")
            raise SpeechModelUnavailable(detail="pip install faster-whisper") from exc
        s = settings()
        _status.update(state="loading", error=None)
        errors = []
        for device, compute_type in _device_plan(s):
            started = time.perf_counter()
            try:
                log.info("[RUN]   loading Whisper %s on %s (%s)", s["whisper_model"], device, compute_type)
                model = WhisperModel(s["whisper_model"], device=device, compute_type=compute_type,
                                     cpu_threads=os.cpu_count() or 4)
                # One tiny pass proves the device works (a GPU without cuDNN/cuBLAS fails only here).
                list(model.transcribe(np.zeros(SAMPLE_RATE, dtype=np.float32), language=ARABIC_LANGUAGE,
                                      task=TASK, beam_size=1, without_timestamps=True)[0])
            except Exception as exc:  # noqa: BLE001 - try the next device
                log.warning("[WARN]  Whisper on %s failed -> %s: %s", device, type(exc).__name__, exc)
                errors.append(f"{device}: {type(exc).__name__}: {exc}")
                continue
            _model = model
            _status.update(state="ready", device=device, compute_type=compute_type, error=None)
            log.info("[OK]    Whisper %s ready on %s in %.0f s (language=%s, task=%s)", s["whisper_model"],
                     device, time.perf_counter() - started, ARABIC_LANGUAGE, TASK)
            return _model
        _status.update(state="unavailable", error="; ".join(errors)[:500])
        raise SpeechModelUnavailable(detail="; ".join(errors)[:500])


def warm_up() -> None:
    """Load the model now (called in the background at API start-up) instead of on the first question."""
    try:
        _load()
    except SpeechError as exc:
        log.error("[FAIL]  speech model not loaded -> %s", exc.detail or exc.code)


# ---------------------------------------------------------------- transcription

def _decode(audio_bytes: bytes) -> np.ndarray:
    """Any browser recording (webm/opus, ogg, mp4, wav) -> 16 kHz mono float32.

    Uses PyAV directly: faster-whisper's decode_audio passes an option that PyAV >= 15 removed.
    """
    if not audio_bytes:
        raise InvalidAudio(detail="empty audio")
    try:
        import av
        from av.audio.resampler import AudioResampler
    except ImportError as exc:
        raise SpeechModelUnavailable(detail="pip install faster-whisper (PyAV)") from exc
    chunks: list[np.ndarray] = []
    try:
        resampler = AudioResampler(format="s16", layout="mono", rate=SAMPLE_RATE)
        with av.open(io.BytesIO(audio_bytes), mode="r") as container:
            frames = container.decode(audio=0)
            while True:
                try:
                    frame = next(frames)
                except StopIteration:
                    break
                except av.error.InvalidDataError:   # a damaged frame (e.g. the last one of a stopped recording)
                    continue
                chunks.extend(out.to_ndarray().reshape(-1) for out in resampler.resample(frame))
            chunks.extend(out.to_ndarray().reshape(-1) for out in resampler.resample(None))
    except Exception as exc:  # noqa: BLE001 - PyAV raises many types for a broken file
        raise InvalidAudio(detail=f"{type(exc).__name__}: {exc}") from exc
    if not chunks:
        raise InvalidAudio(detail="no audio frames")
    return np.concatenate(chunks).astype(np.float32) / 32768.0


def _clean(text: str) -> str:
    for phrase in _HALLUCINATIONS:
        text = text.replace(phrase, " ")
    return " ".join(text.split()).strip(" .،")


def ensure_arabic(text: str, min_ratio: float | None = None) -> str:
    """Return the text if it is Arabic; raise NonArabicSpeech / NoSpeechDetected otherwise."""
    if not text:
        raise NoSpeechDetected(detail="empty transcript")
    words = text.split()
    arabic = sum(1 for word in words if _ARABIC_LETTER.search(word))
    other = sum(1 for word in words if not _ARABIC_LETTER.search(word) and _OTHER_LETTER.search(word))
    ratio = arabic / (arabic + other) if arabic + other else 0.0
    if not arabic or ratio < (settings()["min_arabic_ratio"] if min_ratio is None else min_ratio):
        raise NonArabicSpeech(detail=f"arabic words {arabic}, other-script words {other}")
    return text


def _check_spoken_language(model, audio: np.ndarray, s: dict[str, Any]) -> None:
    """Reject speech that is clearly not Arabic. Detection only gates; it never picks the output language."""
    try:   # no voice at all -> "no speech", not "not Arabic" (noise is detected as a random language)
        from faster_whisper.vad import VadOptions, get_speech_timestamps
        if not get_speech_timestamps(audio, VadOptions(min_silence_duration_ms=500)):
            raise NoSpeechDetected(detail="no voice found by VAD")
    except ImportError:
        pass
    try:
        detected, prob, all_probs = model.detect_language(audio, vad_filter=True)   # default VAD options
    except Exception as exc:  # noqa: BLE001 - e.g. no speech left after VAD: transcription decides
        log.warning("[WARN]  language check skipped -> %s: %s", type(exc).__name__, exc)
        return
    arabic_prob = dict(all_probs).get(ARABIC_LANGUAGE, 0.0)
    log.info("[CHECK] spoken language %s (%.2f), Arabic %.2f", detected, prob, arabic_prob)
    if (detected != ARABIC_LANGUAGE and prob >= s["other_language_min_prob"]
            and arabic_prob < s["arabic_max_prob_to_reject"]):
        raise NonArabicSpeech(detail=f"spoken language {detected} ({prob:.2f}), Arabic {arabic_prob:.2f}")


@log_step(summary=lambda text: f"{len(text.split())} Arabic words")
def transcribe(audio_bytes: bytes, language: str = ARABIC_LANGUAGE) -> str:
    """Return the Arabic transcript of the recorded audio (Whisper Large-v3, Arabic only)."""
    if language != ARABIC_LANGUAGE:
        raise ValueError(f"Sanad speech-to-text is Arabic only (language='{ARABIC_LANGUAGE}'), got {language!r}")
    s = settings()
    audio = _decode(bytes(audio_bytes))
    seconds = len(audio) / SAMPLE_RATE
    if seconds < 0.3 or float(np.abs(audio).max(initial=0.0)) < 1e-4:
        raise NoSpeechDetected(detail=f"{seconds:.1f} s of silence")
    if seconds > s["max_seconds"]:
        raise InvalidAudio(f"التسجيل أطول من {int(s['max_seconds'])} ثانية. سجّل سؤالًا أقصر.",
                           detail=f"{seconds:.0f} s > {s['max_seconds']} s")
    model = _load()
    started = time.perf_counter()
    with _lock:
        if s["reject_other_languages"]:
            _check_spoken_language(model, audio, s)
        segments, info = model.transcribe(
            audio,
            language=ARABIC_LANGUAGE,          # fixed: no language detection, no other output language
            task=TASK,                         # fixed: transcribe, never translate
            beam_size=int(s["beam_size"]),
            vad_filter=True,                   # drop silence (Whisper invents text on silence)
            vad_parameters={"min_silence_duration_ms": 500},
            condition_on_previous_text=False,  # no drift between segments
            initial_prompt=s["initial_prompt"] or None,
            without_timestamps=True,
        )
        kept = [seg.text for seg in segments if not (seg.no_speech_prob > 0.6 and seg.avg_logprob < -1.0)]
    text = _clean(" ".join(kept))
    log.info("[RESULT] %.1f s audio (%.1f s speech) -> %d chars in %.1f s on %s", seconds,
             getattr(info, "duration_after_vad", seconds) or 0.0, len(text), time.perf_counter() - started,
             _status.get("device"))
    return ensure_arabic(text)
