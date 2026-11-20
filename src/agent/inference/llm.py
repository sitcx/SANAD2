"""Claude client used by every agent and tool that needs the LLM.

Every caller must work without the LLM too: when ANTHROPIC_API_KEY is missing
(or a call fails) the tools fall back to simple rules so the demo never breaks.
"""
from __future__ import annotations

from functools import lru_cache
from typing import TypeVar

from pydantic import BaseModel

from src.agent.core.config import get_config, get_secret
from src.logger import get_logger

log = get_logger("inference.llm")


def llm_available() -> bool:
    """True when an Anthropic API key is configured."""
    return bool(get_secret("ANTHROPIC_API_KEY"))


@lru_cache(maxsize=1)
def get_llm():
    """Return the chat model named in config.yaml (llm.model).

    Raises RuntimeError when ANTHROPIC_API_KEY is not set.
    """
    api_key = get_secret("ANTHROPIC_API_KEY")
    if not api_key:
        log.error("[FAIL]  Claude client -> ANTHROPIC_API_KEY is not set")
        raise RuntimeError("ANTHROPIC_API_KEY is not set (add it to .env)")
    from langchain_anthropic import ChatAnthropic

    settings = get_config().get("llm", {})
    model = settings.get("model", "claude-sonnet-5-5")
    log.info("[OK]    Claude client ready (model=%s)", model)
    return ChatAnthropic(
        model=model,
        api_key=api_key,
        max_tokens=settings.get("max_tokens", 1024),
        timeout=settings.get("timeout", 30),
        max_retries=2,
    )


T = TypeVar("T", bound=BaseModel)


def ask_claude(prompt: str, schema: type[T]) -> T:
    """Ask Claude and get back a validated `schema` instance (see src/agent/schemas.py).

    Uses Claude's native structured output (method="json_schema"): the reply is JSON that matches the
    schema, so there is nothing to cut out of the text. (Forced tool calling, langchain's default, is
    not supported on claude-sonnet-5-5.) pydantic then checks the limits (e.g. match 0-100).
    Raises on a missing key, a network error or a reply that fails validation; callers fall back to rules.
    """
    reply = get_llm().with_structured_output(schema, method="json_schema").invoke(prompt)
    return reply if isinstance(reply, schema) else schema.model_validate(reply)
