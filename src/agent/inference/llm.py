"""Claude client used by every agent and tool that needs the LLM.

The provider is set in config.yaml (llm.provider):
    openrouter  Claude through OpenRouter's Anthropic-compatible Messages API (https://openrouter.ai/api),
                key OPENROUTER_API_KEY, model ids like "anthropic/claude-sonnet-5.5"
    anthropic   Claude directly, key ANTHROPIC_API_KEY, model ids like "claude-sonnet-5-5"
Both speak the same Messages API (tools, web search, structured output), so the agents do not change.
Every caller must work without the LLM too: when the key is missing (or a call fails) the tools fall back
to simple rules so the demo never breaks.
"""
from __future__ import annotations

from functools import lru_cache
from typing import TypeVar

from pydantic import BaseModel

from src.agent.core.config import get_config, get_secret
from src.logger import get_logger

log = get_logger("inference.llm")


OPENROUTER_BASE_URL = "https://openrouter.ai/api"   # the SDK appends /v1/messages


def settings(scope: str | None = None) -> dict:
    """The `llm` block of config.yaml, overridden by `<scope>.llm` (e.g. job_agent.llm uses Anthropic directly)."""
    config = get_config()
    merged = dict(config.get("llm", {}))
    if scope:
        merged.update((config.get(scope) or {}).get("llm") or {})
    return merged


def provider(scope: str | None = None) -> str:
    return settings(scope).get("provider", "anthropic")


def api_key(scope: str | None = None) -> str | None:
    return get_secret("OPENROUTER_API_KEY" if provider(scope) == "openrouter" else "ANTHROPIC_API_KEY")


def base_url(scope: str | None = None) -> str | None:
    return OPENROUTER_BASE_URL if provider(scope) == "openrouter" else None


def model_id(scope: str | None = None) -> str:
    return settings(scope).get("model", "claude-sonnet-5-5")


def llm_available(scope: str | None = None) -> bool:
    """True when the key of the provider used by this scope is set."""
    return bool(api_key(scope))


def anthropic_client(timeout: float = 180, scope: str | None = None):
    """The official Anthropic SDK client for the scope's provider (used by tool loops and file input)."""
    import anthropic

    return anthropic.Anthropic(api_key=api_key(scope), base_url=base_url(scope), timeout=timeout, max_retries=2)


def fallback_params(scope: str | None = None) -> dict:
    """Server-side refusal fallback: a declined request is re-run on a fallback model (Anthropic API only)."""
    return {} if provider(scope) == "openrouter" else {"betas": ["server-side-fallback-2026-07-01"], "fallbacks": "default"}


class ClaudeChat:
    """Structured replies through the official Anthropic SDK (works the same on the Anthropic API and OpenRouter).

    Keeps the small interface the agents already use: with_structured_output(schema, method="json_schema").invoke(prompt).
    messages.parse sends Claude's native structured output and returns a validated pydantic object.
    """

    def __init__(self, model: str, max_tokens: int, timeout: float, effort: str | None, scope: str | None = None):
        self.model, self.max_tokens, self.timeout, self.effort, self.scope = model, max_tokens, timeout, effort, scope

    def model_copy(self, update: dict) -> ClaudeChat:
        return ClaudeChat(self.model, update.get("max_tokens", self.max_tokens), update.get("default_request_timeout", self.timeout),
                          self.effort, self.scope)

    def with_structured_output(self, schema, method: str | None = None):
        chat = self

        class Runner:
            def invoke(self, prompt: str):
                request = {"model": chat.model, "max_tokens": chat.max_tokens, "output_format": schema,
                           "messages": [{"role": "user", "content": prompt}]}
                if chat.effort:
                    request["output_config"] = {"effort": chat.effort}
                response = anthropic_client(chat.timeout, chat.scope).messages.parse(**request)
                if response.stop_reason == "refusal" or response.parsed_output is None:
                    raise RuntimeError(f"no structured reply (stop_reason={response.stop_reason})")
                return response.parsed_output
        return Runner()


@lru_cache(maxsize=8)
def get_llm(scope: str | None = None) -> ClaudeChat:
    """Return the chat model for a scope (config `llm`, overridden by `<scope>.llm`).

    Raises RuntimeError when the provider's key is not set.
    """
    if not api_key(scope):
        name = "OPENROUTER_API_KEY" if provider(scope) == "openrouter" else "ANTHROPIC_API_KEY"
        log.error("[FAIL]  Claude client -> %s is not set", name)
        raise RuntimeError(f"{name} is not set (add it to .env)")
    conf = settings(scope)
    log.info("[OK]    Claude client ready (scope=%s, provider=%s, model=%s)", scope or "default", provider(scope), model_id(scope))
    # max_tokens covers adaptive thinking plus the reply, so leave room; effort keeps replies quick and cheap.
    return ClaudeChat(model_id(scope), conf.get("max_tokens", 4096), conf.get("timeout", 60), conf.get("effort", "medium"), scope)


T = TypeVar("T", bound=BaseModel)


def ask_claude(prompt: str, schema: type[T], *, max_tokens: int | None = None, timeout: float | None = None,
               scope: str | None = None) -> T:
    """Ask Claude and get back a validated `schema` instance (see src/agent/schemas.py).

    Uses Claude's native structured output (messages.parse): the reply is JSON that matches the schema,
    so there is nothing to cut out of the text. (Forced tool calling is not supported on claude-sonnet-5-5.)
    pydantic then checks the limits (e.g. match 0-100).
    Raises on a missing key, a network error or a reply that fails validation; callers fall back to rules.
    """
    llm = get_llm(scope) if scope else get_llm()
    if (max_tokens or timeout) and hasattr(llm, "model_copy"):   # a long reading (e.g. a whole CV) needs more room than the default
        llm = llm.model_copy(update={k: v for k, v in (("max_tokens", max_tokens), ("default_request_timeout", timeout)) if v})
    reply = llm.with_structured_output(schema, method="json_schema").invoke(prompt)
    return reply if isinstance(reply, schema) else schema.model_validate(reply)
