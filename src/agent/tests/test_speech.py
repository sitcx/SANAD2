"""Arabic-only speech-to-text (src/agent/speech): rules, agent wiring and WebSocket errors.

The Whisper model itself is not loaded here (it is ~3 GB); see docs/speech.md for the live test.
"""
from __future__ import annotations

import base64
import importlib

import pytest
from fastapi.testclient import TestClient

from src.agent import api
from src.agent.interview_agent.graph import InterviewSession
from src.agent.speech import speech
from src.agent.speech.speech import ARABIC_LANGUAGE, TASK, NonArabicSpeech, NoSpeechDetected, ensure_arabic

# the module, not the same-named function that tools/__init__.py exports
stt_module = importlib.import_module("src.agent.interview_agent.tools.speech_to_text")


def test_language_and_task_are_fixed_to_arabic_transcription():
    assert ARABIC_LANGUAGE == "ar"
    assert TASK == "transcribe"
    assert speech.model_status()["language"] == "ar"
    with pytest.raises(ValueError, match="Arabic only"):
        speech.transcribe(b"audio", language="en")


@pytest.mark.parametrize("text", ["حدثنا عن خبرتك في تحليل البيانات", "ما خبرتك في Excel و SQL؟"])
def test_arabic_text_is_kept(text):
    assert ensure_arabic(text) == text


@pytest.mark.parametrize("text", ["Tell me about your experience", "Bonjour, parlez-moi de vous", "123 456"])
def test_non_arabic_text_is_rejected(text):
    with pytest.raises(NonArabicSpeech) as error:
        ensure_arabic(text)
    assert error.value.code == "non_arabic_speech"
    assert "العربي" in error.value.message


def test_empty_transcript_is_no_speech():
    with pytest.raises(NoSpeechDetected):
        ensure_arabic("")


def test_known_silence_hallucinations_are_removed():
    assert speech._clean(" ترجمة نانسي قنقر ") == ""
    assert speech._clean("ما هي خبرتك؟ اشتركوا في القناة") == "ما هي خبرتك؟"


def test_broken_audio_is_invalid_audio():
    pytest.importorskip("faster_whisper")
    with pytest.raises(speech.InvalidAudio):
        speech.transcribe(b"not audio at all")


def test_recordings_are_decoded_to_16khz_mono():
    pytest.importorskip("av")
    import io as _io
    import wave

    import numpy as np
    buffer = _io.BytesIO()
    with wave.open(buffer, "wb") as w:   # 1 s stereo 44.1 kHz tone, like a browser capture
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(44_100)
        tone = (np.sin(np.linspace(0, 440 * 2 * np.pi, 44_100)) * 8000).astype(np.int16)
        w.writeframes(np.repeat(tone, 2).tobytes())
    audio = speech._decode(buffer.getvalue())
    assert audio.dtype == np.float32
    assert abs(len(audio) - 16_000) < 400
    assert 0.1 < float(np.abs(audio).max()) <= 1.0


def test_agent_stores_the_arabic_transcript_as_the_question(monkeypatch):
    monkeypatch.setattr(stt_module, "transcribe", lambda audio: "حدثنا عن خبرتك")
    session = InterviewSession("speech-1", "ai")
    state = session.send({"type": "question", "audio": b"\x00" * 2000})
    assert state["last_question"] == "حدثنا عن خبرتك"


def _start(ws):
    ws.send_json({"type": "start", "mode": "ai"})
    assert ws.receive_json()["type"] == "started"


def test_websocket_audio_question_returns_arabic_text(monkeypatch):
    monkeypatch.setattr(stt_module, "transcribe", lambda audio: "ما هي مهاراتك؟")
    with TestClient(api.app) as client, client.websocket_connect("/interview/speech-ws") as ws:
        _start(ws)
        ws.send_json({"type": "question", "audio_b64": base64.b64encode(b"\x00" * 2000).decode()})
        reply = ws.receive_json()
    assert reply["type"] == "state"
    assert reply["last_question"] == "ما هي مهاراتك؟"


def test_websocket_non_arabic_speech_gets_an_arabic_error_and_the_interview_continues(monkeypatch):
    def english(_audio):
        raise NonArabicSpeech(detail="english")
    monkeypatch.setattr(stt_module, "transcribe", english)
    with TestClient(api.app) as client, client.websocket_connect("/interview/speech-err") as ws:
        _start(ws)
        ws.send_json({"type": "question", "audio_b64": base64.b64encode(b"\x00" * 2000).decode()})
        error = ws.receive_json()
        ws.send_json({"type": "question", "text": "حدثنا عن نفسك"})
        after = ws.receive_json()
    assert error == {"type": "error", "error": "non_arabic_speech", "details": [NonArabicSpeech.message]}
    assert after["last_question"] == "حدثنا عن نفسك"


def test_websocket_invalid_base64_is_invalid_audio():
    with TestClient(api.app) as client, client.websocket_connect("/interview/speech-b64") as ws:
        _start(ws)
        ws.send_json({"type": "question", "audio_b64": "%%% not base64 %%%"})
        error = ws.receive_json()
    assert error["error"] == "invalid_audio"
    assert error["details"]


def test_speech_status_endpoint():
    with TestClient(api.app) as client:
        body = client.get("/speech/status").json()
    assert body["language"] == "ar" and body["task"] == "transcribe" and body["model"] == "large-v3"


class _FakeModel:
    def __init__(self, language, prob, arabic):
        self.result = (language, prob, [(language, prob), ("ar", arabic)])

    def detect_language(self, audio, **_):
        return self.result


@pytest.fixture
def voice_found(monkeypatch):
    vad = pytest.importorskip("faster_whisper.vad")
    monkeypatch.setattr(vad, "get_speech_timestamps", lambda audio, options: [{"start": 0, "end": 16000}])


def test_silence_is_no_speech_not_another_language():
    pytest.importorskip("faster_whisper.vad")
    import numpy as np
    with pytest.raises(NoSpeechDetected):
        speech._check_spoken_language(_FakeModel("nn", 0.9, 0.0), np.zeros(32000, dtype=np.float32), speech.settings())


def test_clearly_other_spoken_language_is_rejected(voice_found):
    with pytest.raises(NonArabicSpeech):
        speech._check_spoken_language(_FakeModel("en", 0.97, 0.01), None, speech.settings())


@pytest.mark.parametrize("language, prob, arabic", [("ar", 0.95, 0.95), ("fa", 0.45, 0.30), ("ur", 0.6, 0.35)])
def test_arabic_or_uncertain_speech_is_transcribed(language, prob, arabic, voice_found):
    speech._check_spoken_language(_FakeModel(language, prob, arabic), None, speech.settings())
