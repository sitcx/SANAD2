"""Live Arabic captions: segmentation, partial/final captions, Arabic-only, and the WebSocket path.

OpenRouter and the voice detector are replaced by fakes; nothing leaves the machine.
"""
from __future__ import annotations

import asyncio
import json

import httpx
import numpy as np
import pytest
from fastapi.testclient import TestClient

from src.agent import api
from src.agent.speech import live as live_module
from src.agent.speech import openrouter
from src.agent.speech.live import BYTES_PER_SECOND, LiveCaptions
from src.agent.speech.openrouter import SpeechNotConfigured, SpeechServiceUnavailable, Transcript
from src.agent.speech.speech import NonArabicSpeech

CHUNK = BYTES_PER_SECOND // 10          # 100 ms frames, like the browser


def tone(seconds: float) -> bytes:
    return (np.full(int(16_000 * seconds), 6000, dtype=np.int16)).tobytes()


def silence(seconds: float) -> bytes:
    return np.zeros(int(16_000 * seconds), dtype=np.int16).tobytes()


def loud(pcm: bytes) -> list[tuple[int, int]]:   # fake voice detector: the span of loud samples
    idx = np.flatnonzero(np.abs(np.frombuffer(pcm, dtype=np.int16)) > 1000)
    return [(int(idx[0]), int(idx[-1]) + 1)] if idx.size else []


def frames(pcm: bytes):
    for i in range(0, len(pcm), CHUNK):
        yield pcm[i:i + CHUNK]


class Recorder:
    def __init__(self):
        self.partials, self.finals, self.errors = [], [], []

    async def on_partial(self, utterance, text):
        self.partials.append((utterance, text))

    async def on_final(self, utterance, text):
        self.finals.append((utterance, text))

    async def on_error(self, exc):
        self.errors.append(exc.code)


async def _run(transcribe, audio: bytes) -> Recorder:
    rec = Recorder()
    captions = LiveCaptions(on_partial=rec.on_partial, on_final=rec.on_final, on_error=rec.on_error,
                            transcribe=transcribe, detect=loud)
    for frame in frames(audio):
        await captions.feed(frame)
        await asyncio.sleep(0)               # let partial tasks run, like a real stream
    await captions.drain()
    await captions.close()
    return rec


def test_speech_gives_growing_partials_then_one_final():
    async def transcribe(pcm, final):
        return Transcript(text="حدثنا عن خبرتك" if final else "حدثنا", language="ar", seconds=0)
    rec = asyncio.run(_run(transcribe, silence(1) + tone(2.5) + silence(1.5)))
    assert rec.partials and all(text == "حدثنا" for _, text in rec.partials)
    assert rec.finals == [(1, "حدثنا عن خبرتك")]
    assert rec.errors == []


def test_two_sentences_are_finalized_separately_in_order():
    async def transcribe(pcm, final):
        return Transcript(text=f"جملة {round(len(pcm) / BYTES_PER_SECOND)}", language="ar", seconds=0)
    rec = asyncio.run(_run(transcribe, tone(1.5) + silence(1.2) + tone(3) + silence(1.2)))
    assert [u for u, _ in rec.finals] == [1, 2]


def test_short_noise_and_silence_send_nothing():
    calls = []

    async def transcribe(pcm, final):
        calls.append(final)
        return Transcript(text="كلام", language="ar", seconds=0)
    rec = asyncio.run(_run(transcribe, silence(2) + tone(0.1) + silence(2)))
    assert rec.finals == [] and calls == []


def test_non_arabic_sentence_is_an_error_not_a_question():
    async def transcribe(pcm, final):
        raise NonArabicSpeech(detail="spoken language en")
    rec = asyncio.run(_run(transcribe, tone(2) + silence(1.5)))
    assert rec.finals == [] and rec.partials == []
    assert rec.errors == ["non_arabic_speech"]


def test_service_errors_are_reported_once_not_every_second():
    async def transcribe(pcm, final):
        raise SpeechServiceUnavailable(detail="HTTP 503")
    rec = asyncio.run(_run(transcribe, tone(4) + silence(1.5)))
    assert rec.errors == ["speech_service_unavailable"]


def test_long_speech_is_cut_at_the_limit(isolated):
    isolated.setdefault("speech", {}).setdefault("live", {})["max_utterance_s"] = 2
    live_module.get_config = lambda: isolated

    async def transcribe(pcm, final):
        return Transcript(text="كلام طويل", language="ar", seconds=0)
    try:
        rec = asyncio.run(_run(transcribe, tone(5) + silence(1.5)))
    finally:
        live_module.get_config = openrouter.get_config
    assert len(rec.finals) >= 2


# ---------------------------------------------------------------- OpenRouter request / response

def _client(handler):
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def test_openrouter_request_is_arabic_safe_and_key_stays_in_the_header(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    seen = {}

    def handler(request):
        seen["auth"] = request.headers["Authorization"]
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"text": " لماذا تريد العمل معنا؟ ", "language": "arabic"})

    async def go():
        async with _client(handler) as client:
            return await openrouter.transcribe_pcm(client, tone(1), final=True)
    result = asyncio.run(go())
    assert result.text == "لماذا تريد العمل معنا؟"
    body = seen["body"]
    assert seen["auth"] == "Bearer sk-or-test" and "sk-or-test" not in json.dumps(body)
    assert body["model"] == "openai/whisper-large-v3"
    assert body["response_format"] == "verbose_json" and "language" not in body   # detection gates Arabic
    assert body["provider"] == {"zdr": True}
    assert body["input_audio"]["format"] == "wav"


def test_openrouter_other_language_is_rejected(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")

    async def go():
        async with _client(lambda r: httpx.Response(200, json={"text": "Tell me", "language": "en"})) as client:
            await openrouter.transcribe_pcm(client, tone(1), final=True)
    with pytest.raises(NonArabicSpeech):
        asyncio.run(go())


@pytest.mark.parametrize("status, words", [(401, "مفتاح"), (402, "رصيد"), (429, "انتظر"), (503, "غير متاحة")])
def test_openrouter_http_errors_have_arabic_messages(monkeypatch, status, words):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")

    async def go():
        async with _client(lambda r: httpx.Response(status, json={"error": {"message": "x"}})) as client:
            await openrouter.transcribe_pcm(client, tone(1), final=True)
    with pytest.raises(SpeechServiceUnavailable) as error:
        asyncio.run(go())
    assert words in error.value.message


def test_missing_key_is_not_configured(monkeypatch):
    monkeypatch.setattr(openrouter, "get_secret", lambda name: None)
    with pytest.raises(SpeechNotConfigured):
        openrouter.api_key()


# ---------------------------------------------------------------- WebSocket: binary audio -> captions -> agent

def test_websocket_live_audio_gives_captions_and_sends_the_sentence_to_the_agent(monkeypatch):
    async def transcribe(pcm, final):
        return Transcript(text="ما هي مهاراتك؟" if final else "ما هي", language="ar", seconds=0)

    monkeypatch.setattr(api, "openrouter_key", lambda: "sk-or-test")
    monkeypatch.setattr(api, "LiveCaptions",
                        lambda **kw: LiveCaptions(**kw, transcribe=transcribe, detect=loud))
    replies = []
    with TestClient(api.app) as client, client.websocket_connect("/interview/live-1") as ws:
        ws.send_json({"type": "start", "mode": "ai"})
        assert ws.receive_json()["type"] == "started"
        for frame in frames(tone(2) + silence(1.5)):
            ws.send_bytes(frame)
        while True:
            reply = ws.receive_json()
            replies.append(reply)
            if reply["type"] == "state":
                break
    finals = [r for r in replies if r["type"] == "caption" and r["final"]]
    assert finals == [{"type": "caption", "utterance": 1, "text": "ما هي مهاراتك؟", "final": True}]
    assert replies[-1]["last_question"] == "ما هي مهاراتك؟"


def test_websocket_live_audio_without_key_gets_an_arabic_error(monkeypatch):
    def no_key():
        raise SpeechNotConfigured()
    monkeypatch.setattr(api, "openrouter_key", no_key)
    with TestClient(api.app) as client, client.websocket_connect("/interview/live-2") as ws:
        ws.send_json({"type": "start", "mode": "ai"})
        ws.receive_json()
        ws.send_bytes(tone(0.1))
        error = ws.receive_json()
        ws.send_json({"type": "question", "text": "حدثنا عن نفسك"})   # typed questions still work
        state = ws.receive_json()
    assert error["error"] == "speech_not_configured" and "OpenRouter" in error["details"][0]
    assert state["last_question"] == "حدثنا عن نفسك"
