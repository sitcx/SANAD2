"""Shared logger for all Sanad agents.

Log file: src/logger/logs/sanad.log (config.yaml -> logging.file; the folder is created automatically).

Every line shows which request it belongs to and whether each step worked:

    10:42:01 | INFO  | req-7f3a | job_agent.read_cv     | [START] read_cv
    10:42:01 | INFO  | req-7f3a | job_agent.read_cv     | [FALLBACK] no ANTHROPIC_API_KEY -> rules
    10:42:01 | INFO  | req-7f3a | job_agent.read_cv     | [OK]    read_cv (12 ms) -> skills=4 city=riyadh
    10:42:01 | INFO  | req-7f3a | job_agent             | [DECISION] 1 job < min_matches 3 -> widen search
    10:42:02 | ERROR | req-7f3a | job_agent.score_job   | [FAIL]  score_job (3 ms) -> KeyError: 'id'

Tags: [START] [OK] [FAIL] step result | [DECISION] graph routing | [LLM] / [FALLBACK] which path
was used | [REQUEST] / [RESPONSE] API traffic | [EVENT] interview events.

Logs agent decisions (chosen option, "None of these" counter, interpreter switch).
Never log CV contents or other personal data: summaries contain counts and ids only.
"""
from __future__ import annotations

import contextvars
import functools
import logging
import os
import sys
import time
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

from src.agent.core.config import get_config, project_path

_FORMAT = "%(asctime)s | %(levelname)-7s | %(run_id)-9s | %(short_name)-34s | %(message)s"
_DATE_FORMAT = "%H:%M:%S"
_run_id: contextvars.ContextVar[str] = contextvars.ContextVar("sanad_run_id", default="-")
_configured = False


class _ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.run_id = _run_id.get()
        record.short_name = record.name.removeprefix("sanad.")
        return True


def _configure() -> None:
    global _configured
    if _configured:
        return
    settings = get_config().get("logging", {})
    root = logging.getLogger("sanad")
    root.setLevel(settings.get("level", "INFO"))
    root.propagate = False   # own handlers: uvicorn/pytest logging setup does not change ours
    formatter = logging.Formatter(_FORMAT, _DATE_FORMAT)
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # Arabic on Windows consoles
        except (ValueError, OSError):
            pass
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    # SANAD_LOG_FILE: empty/unset = config.yaml logging.file; "none" = console only.
    log_file = os.getenv("SANAD_LOG_FILE") or settings.get("file")
    if str(log_file).lower() == "none":
        log_file = None
    if log_file:
        path: Path = project_path(log_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(path, encoding="utf-8"))
    for handler in handlers:
        handler.setFormatter(formatter)
        handler.addFilter(_ContextFilter())
        root.addHandler(handler)
    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Return a logger, e.g. get_logger("interview_agent")."""
    _configure()
    return logging.getLogger(f"sanad.{name}")


def new_run_id(prefix: str = "req") -> str:
    """Start a new run id (one per API request / interview session) shown on every log line."""
    run_id = f"{prefix}-{uuid.uuid4().hex[:4]}"
    _run_id.set(run_id)
    return run_id


def set_run_id(run_id: str) -> None:
    _run_id.set(run_id)


def log_step(summary: Callable[[Any], str] | None = None, name: str | None = None):
    """Decorator: log [START], then [OK] with duration and a short result summary, or [FAIL].

    summary(result) must return counts/ids only, never personal data.
    """
    def decorator(fn):
        step = name or fn.__name__
        # src.agent.job_agent.tools.read_cv -> "job_agent.read_cv", src.database.db -> "database.db"
        logger = get_logger(fn.__module__.removeprefix("src.agent.").removeprefix("src.").replace(".tools.", "."))

        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            logger.info("[START] %s", step)
            started = time.perf_counter()
            try:
                result = fn(*args, **kwargs)
            except Exception as exc:
                ms = (time.perf_counter() - started) * 1000
                logger.error("[FAIL]  %s (%.0f ms) -> %s: %s", step, ms, type(exc).__name__, exc)
                raise
            ms = (time.perf_counter() - started) * 1000
            details = ""
            if summary:
                try:
                    details = f" -> {summary(result)}"
                except Exception:  # noqa: BLE001 - a bad summary must not break the step
                    details = ""
            logger.info("[OK]    %s (%.0f ms)%s", step, ms, details)
            return result

        return wrapper

    return decorator
