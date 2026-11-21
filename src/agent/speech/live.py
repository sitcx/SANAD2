"""Live Arabic captions from a continuous microphone stream.

The browser streams 16 kHz mono 16-bit PCM over WS /interview/{session} (binary frames). This module:
    1. finds speech with a voice-activity detector (Silero VAD, bundled with faster-whisper);
    2. while someone is speaking, re-transcribes the sentence in progress about every
       `partial_interval_s` and emits a partial caption (the text grows on screen);
    3. after `end_silence_ms` of silence (or `max_utterance_s`), transcribes the whole sentence once
       more, checks it is Arabic, and emits the final caption -> the Interview Agent.

OpenRouter (src/agent/speech/openrouter.py) has no streaming speech-to-text API, so step 2 is how
live captions are produced. A provider with a true streaming API can replace `transcribe` without
changing the browser or the agent.
"""
from __future__ import annotations

import asyncio
from collections import deque
from typing import Any, Awaitable, Callable

import httpx
import numpy as np

from src.agent.core.config import get_config
from src.logger import get_logger

from .openrouter import SAMPLE_RATE, Transcript, transcribe_pcm
from .speech import NonArabicSpeech, SpeechError

log = get_logger("speech.live")

BYTES_PER_SECOND = SAMPLE_RATE * 2
_DEFAULTS: dict[str, Any] = {
    "partial_interval_s": 1.0,   # how often the caption of the sentence in progress is refreshed
    "end_silence_ms": 700,       # this much silence ends a sentence
    "max_utterance_s": 20,       # longer sentences are cut here
    "min_speech_s": 0.3,         # less detected speech than this (a cough, a click) is ignored
    "preroll_s": 0.4,            # audio kept from before speech starts (first syllable)
    "vad_step_ms": 200,          # how often speech/silence is decided
    "vad_window_s": 0.6,
}

Transcribe = Callable[[bytes, bool], Awaitable[Transcript]]
Detect = Callable[[bytes], list[tuple[int, int]]]     # PCM -> speech spans (start, end) in samples


def settings() -> dict[str, Any]:
    return {**_DEFAULTS, **((get_config().get("speech") or {}).get("live") or {})}


def silero_speech_spans(pcm: bytes) -> list[tuple[int, int]]:
    """Speech spans in the window (Silero VAD); falls back to an energy threshold without faster-whisper."""
    audio = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
    if not audio.size:
        return []
    try:
        from faster_whisper.vad import VadOptions, get_speech_timestamps
    except ImportError:
        return [(0, audio.size)] if float(np.sqrt(np.mean(audio ** 2))) > 0.02 else []
    spans = get_speech_timestamps(audio, VadOptions(min_speech_duration_ms=120, min_silence_duration_ms=100,
                                                    speech_pad_ms=0))
    return [(int(s["start"]), int(s["end"])) for s in spans]


class LiveCaptions:
    """One microphone stream. Feed PCM with feed(); results arrive through the callbacks."""

    def __init__(self, *, on_partial: Callable[[int, str], Awaitable[None]],
                 on_final: Callable[[int, str], Awaitable[None]],
                 on_error: Callable[[SpeechError], Awaitable[None]],
                 transcribe: Transcribe | None = None, detect: Detect | None = None):
        self.s = settings()
        self._on_partial, self._on_final, self._on_error = on_partial, on_final, on_error
        self._client: httpx.AsyncClient | None = None
        self._transcribe = transcribe or self._openrouter
        self._detect = detect or silero_speech_spans
        self._window: deque[bytes] = deque()            # last vad_window_s of audio
        self._window_bytes = 0
        self._preroll: deque[bytes] = deque()
        self._preroll_bytes = 0
        self._utterance = bytearray()
        self._speaking = False
        self._silence_ms = 0
        self._speech_ms = 0
        self._since_vad = 0
        self._since_partial = 0
        self._utterance_id = 0
        self._partial_task: asyncio.Task | None = None
        self._final_lock = asyncio.Lock()               # finals are delivered in order
        self._tasks: set[asyncio.Task] = set()
        self._last_error_code: str | None = None

    async def _openrouter(self, pcm: bytes, final: bool) -> Transcript:
        if self._client is None:
            self._client = httpx.AsyncClient()
        return await transcribe_pcm(self._client, pcm, final=final)

    # ------------------------------------------------------------ audio in

    async def feed(self, pcm: bytes) -> None:
        if len(pcm) % 2:
            pcm = pcm[:-1]
        if not pcm:
            return
        self._push(self._window, pcm, "_window_bytes", self.s["vad_window_s"])
        if self._speaking:
            self._utterance.extend(pcm)
        else:
            self._push(self._preroll, pcm, "_preroll_bytes", self.s["preroll_s"])
        ms = len(pcm) * 1000 // BYTES_PER_SECOND
        self._since_vad += ms
        self._since_partial += ms
        if self._since_vad < self.s["vad_step_ms"]:
            return
        step, self._since_vad = self._since_vad, 0
        window = b"".join(self._window)
        spans = await asyncio.to_thread(self._detect, window)
        samples = len(window) // 2
        newest_has_speech = any(end > samples - step * SAMPLE_RATE // 1000 for _, end in spans)
        if newest_has_speech and not self._speaking:
            self._start_utterance()
        if self._speaking:
            if newest_has_speech:
                self._speech_ms += step
            # silence = time since the last detected speech (not since the whole window went quiet)
            self._silence_ms = ((samples - max(end for _, end in spans)) * 1000 // SAMPLE_RATE if spans
                                else self._silence_ms + step)
        if not self._speaking:
            return
        seconds = len(self._utterance) / BYTES_PER_SECOND
        if self._silence_ms >= self.s["end_silence_ms"] or seconds >= self.s["max_utterance_s"]:
            await self.end()
        elif self._since_partial >= self.s["partial_interval_s"] * 1000 and not self._partial_running():
            self._since_partial = 0
            self._partial_task = self._spawn(self._partial(self._utterance_id, bytes(self._utterance)))

    async def end(self) -> None:
        """Finish the sentence in progress (silence, the length limit, or the microphone was muted)."""
        if not self._speaking:
            return
        pcm, utterance_id, speech_ms = bytes(self._utterance), self._utterance_id, self._speech_ms
        self._speaking, self._utterance, self._silence_ms, self._speech_ms = False, bytearray(), 0, 0
        self._preroll.clear()
        self._preroll_bytes = 0
        if speech_ms < self.s["min_speech_s"] * 1000:
            log.info("[RESULT] sentence %d: %d ms of speech -> ignored", utterance_id, speech_ms)
            return
        self._spawn(self._final(utterance_id, pcm))

    async def close(self) -> None:
        for task in list(self._tasks):
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        if self._client is not None:
            await self._client.aclose()

    async def drain(self) -> None:
        """Wait for pending transcriptions (tests)."""
        while self._tasks:
            await asyncio.gather(*list(self._tasks), return_exceptions=True)

    # ------------------------------------------------------------ internals

    def _push(self, buffer: deque, pcm: bytes, counter: str, seconds: float) -> None:
        buffer.append(pcm)
        setattr(self, counter, getattr(self, counter) + len(pcm))
        limit = int(seconds * BYTES_PER_SECOND)
        while getattr(self, counter) - len(buffer[0]) >= limit and len(buffer) > 1:
            setattr(self, counter, getattr(self, counter) - len(buffer.popleft()))

    def _start_utterance(self) -> None:
        self._speaking = True
        self._utterance_id += 1
        self._utterance = bytearray(b"".join(self._preroll))
        self._since_partial = 0
        log.info("[RUN]   sentence %d started", self._utterance_id)

    def _partial_running(self) -> bool:
        return self._partial_task is not None and not self._partial_task.done()

    def _spawn(self, coro) -> asyncio.Task:
        task = asyncio.create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return task

    async def _partial(self, utterance_id: int, pcm: bytes) -> None:
        try:
            result = await self._transcribe(pcm, False)
        except NonArabicSpeech:
            return          # the final result reports it once
        except SpeechError as exc:
            await self._report(exc)
            return
        if result.text and utterance_id == self._utterance_id and self._speaking:
            await self._on_partial(utterance_id, result.text)

    async def _final(self, utterance_id: int, pcm: bytes) -> None:
        async with self._final_lock:
            try:
                result = await self._transcribe(pcm, True)
            except SpeechError as exc:
                await self._report(exc)
                return
            if not result.text:
                log.info("[RESULT] sentence %d: no words (noise)", utterance_id)
                return
            self._last_error_code = None
            log.info("[RESULT] sentence %d final: %d words", utterance_id, len(result.text.split()))
            await self._on_final(utterance_id, result.text)

    async def _report(self, exc: SpeechError) -> None:
        log.warning("[FAIL]  live caption -> %s (%s)", exc.code, exc.detail)
        if exc.code == self._last_error_code and exc.code != NonArabicSpeech.code:
            return          # the same service error once, not every second
        self._last_error_code = exc.code
        await self._on_error(exc)
