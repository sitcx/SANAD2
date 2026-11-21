"""FastAPI app connecting the web UI (src/web) to the agents.

Run from the project root:  uvicorn src.agent.api:app --reload --port 8010

    GET  /health
    POST /jobs/recommend        multipart: cv (pdf/docx/txt/md/json file) | profile (JSON), answers (JSON), name
    WS   /interview/{session}   first message {"type": "start", "mode": "ai"|"human", "job_id"?, "candidate_id"?}
                                then events: {"type": "question", "text"} | {"type": "signs", "segments"}
                                             {"type": "choose", "index": 0..2 | null} | {"type": "interpreter"}
"""
from __future__ import annotations

import base64
import json
import os
import tempfile
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware

from pydantic import ValidationError

from src.agent.interview_agent.graph import InterviewSession, build_interview_graph
from src.agent.schemas import ErrorReply, StartedReply, StartMessage, StateReply, event_message_adapter
from src.agent.job_agent.graph import recommend_jobs
from src.agent.company_api import router as company_router
from src.database import db
from src.logger import get_logger, new_run_id, set_run_id

log = get_logger("api")

CV_SUFFIXES = {".pdf", ".docx", ".txt", ".md", ".json"}
MAX_CV_BYTES = 10 * 1024 * 1024
_interview_graph = build_interview_graph()   # one graph; state kept per session (thread_id)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    db.init_db()
    log.info("[OK]    database ready, API listening")
    yield


app = FastAPI(title="Sanad Agents", lifespan=lifespan)
app.include_router(company_router)
app.add_middleware(
    CORSMiddleware,
    # An empty SANAD_WEB_ORIGINS= in .env means "use the default", not "allow nobody".
    allow_origins=[o.strip() for o in (os.getenv("SANAD_WEB_ORIGINS") or
                                       "http://localhost:3000,http://127.0.0.1:3000").split(",") if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request, call_next):
    run_id = new_run_id("req")
    log.info("[REQUEST] %s %s", request.method, request.url.path)
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception as exc:
        log.error("[FAIL]  %s %s -> %s: %s", request.method, request.url.path, type(exc).__name__, exc)
        raise
    level = log.info if response.status_code < 400 else log.warning
    level("[RESPONSE] %s %s -> %d in %.0f ms", request.method, request.url.path, response.status_code,
          (time.perf_counter() - started) * 1000)
    response.headers["X-Sanad-Run-Id"] = run_id
    return response


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


def _json_form(value: str | None, field: str) -> dict:
    if not value:
        return {}
    try:
        data = json.loads(value)
    except json.JSONDecodeError as exc:
        raise HTTPException(422, f"{field} must be JSON") from exc
    if not isinstance(data, dict):
        raise HTTPException(422, f"{field} must be a JSON object")
    return data


@app.post("/jobs/recommend")
async def jobs_recommend(
    cv: UploadFile | None = File(None),
    profile: str | None = Form(None),
    answers: str | None = Form(None),
    name: str | None = Form(None),
) -> dict:
    """Run the Job Agent. Returns status "need_info" (ask the candidate) or "ok" with jobs."""
    answers_data = _json_form(answers, "answers")
    profile_data = _json_form(profile, "profile")
    if not cv and not profile_data:
        raise HTTPException(422, "send a cv file or a profile")

    tmp_path: Path | None = None
    try:
        if cv and not profile_data:
            suffix = Path(cv.filename or "").suffix.lower()
            if suffix not in CV_SUFFIXES:
                raise HTTPException(415, f"CV must be one of {sorted(CV_SUFFIXES)}")
            content = await cv.read()
            if len(content) > MAX_CV_BYTES:
                raise HTTPException(413, "CV is larger than 10 MB")
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(content)
                tmp_path = Path(tmp.name)
        state = await run_in_threadpool(
            recommend_jobs, cv_file=str(tmp_path) if tmp_path else None,
            answers=answers_data, profile=profile_data or None)
    finally:
        if tmp_path:
            tmp_path.unlink(missing_ok=True)

    if state.get("missing_info"):
        log.info("[RESULT] need_info: %s", state["missing_info"])
        return {"status": "need_info", "missing_info": state["missing_info"], "profile": state["profile"]}
    candidate_id = await run_in_threadpool(db.save_candidate, name or "candidate", state["profile"])
    return {
        "status": "ok",
        "candidate_id": candidate_id,
        "profile": state["profile"],
        "widened": state.get("widened", False),
        "jobs": state.get("jobs", []),
        "recommended": state.get("recommended", []),
    }


def _problems(exc: ValidationError) -> list[str]:
    """Short, readable list of what is wrong with a client message."""
    return [f"{'.'.join(str(p) for p in err['loc']) or 'message'}: {err['msg']}" for err in exc.errors()][:5]


def _event_from_message(message) -> dict:
    """Validated message (schemas.EventMessage) -> event dict for the Interview Agent."""
    event = message.model_dump(exclude_none=True, exclude={"audio_b64"})
    if message.type == "choose":
        event["index"] = message.index          # keep None = "None of these"
    if getattr(message, "audio_b64", None):
        event["audio"] = base64.b64decode(message.audio_b64)
    return event


async def _send(websocket: WebSocket, reply) -> None:
    await websocket.send_json(reply.model_dump(mode="json"))


@app.websocket("/interview/{session_id}")
async def interview(websocket: WebSocket, session_id: str) -> None:
    set_run_id(f"int-{session_id[:5]}")
    await websocket.accept()
    log.info("[REQUEST] WS /interview/%s connected", session_id)
    try:
        try:
            start = StartMessage.model_validate(await websocket.receive_json())
        except ValidationError as exc:
            log.warning("[FAIL]  invalid start message -> %s", _problems(exc))
            await _send(websocket, ErrorReply(error="invalid_message", details=[
                'first message must be {"type": "start", "mode": "ai"|"human"}', *_problems(exc)]))
            await websocket.close(code=1008)
            return
        session = InterviewSession(session_id, start.mode, graph=_interview_graph)
        interview_id = await run_in_threadpool(
            db.start_interview, start.candidate_id, start.job_id, start.mode.value)
        await _send(websocket, StartedReply(interview_id=interview_id, mode=start.mode))

        while True:
            raw = await websocket.receive_json()
            try:
                message = event_message_adapter.validate_python(raw)
            except ValidationError as exc:
                log.warning("[FAIL]  invalid interview message -> %s", _problems(exc))
                await _send(websocket, ErrorReply(error="invalid_message", details=_problems(exc)))
                continue
            try:
                result = await run_in_threadpool(session.send, _event_from_message(message))
            except Exception as exc:  # noqa: BLE001 - keep the interview going
                log.exception("interview event failed: session=%s", session_id)
                await _send(websocket, ErrorReply(error=type(exc).__name__))
                continue
            reply = StateReply.model_validate({k: v for k, v in result.items() if v is not None})
            fields = {"mode": reply.mode.value, "none_count": reply.none_count,
                      "interpreter_called": reply.interpreter_called}
            if reply.interpreter:
                fields["interpreter_reason"] = reply.interpreter["reason"]
            await run_in_threadpool(db.update_interview, interview_id, **fields)
            await _send(websocket, reply)
    except WebSocketDisconnect:
        log.info("interview disconnected: session=%s", session_id)
