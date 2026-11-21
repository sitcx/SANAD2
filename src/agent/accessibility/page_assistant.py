"""Web accessibility assistant: turns the extracted content of a page into a short Arabic spoken guide.

Input:  PageContentRequest (visible elements of the page, in reading order, extracted by the browser).
Output: PageDescriptionReply (validated PageDescriptionResponse + the Arabic text to read aloud).

Steps:
    1. The page is written as numbered lines ("e3 | main | heading h1 | ...") for the LLM.
    2. The LLM (config.yaml -> accessibility; default google/gemini-2.5-flash via OpenRouter) returns JSON
       that pydantic validates as PageDescriptionResponse (schemas.py). One retry on an invalid reply.
    3. Grounding: every element the answer refers to must exist in the extracted page. Unknown ids are
       dropped, labels and section titles are replaced with the page's own text, and the main heading
       must be a heading (or the title) of the page. Nothing the page does not contain is read aloud.
    4. The speech parts are built from the validated, grounded fields (not written freely by the LLM).

Without a key, or when the LLM fails, a rule-based description is built from the same page (via="rules").
The API key is read on the server only and never logged or returned.
"""
from __future__ import annotations

import json
import re
from typing import Any

import httpx
from pydantic import ValidationError

from src.agent.core.config import get_config, get_secret
from src.agent.schemas import (
    PageActionSummary,
    PageClarification,
    PageContentRequest,
    PageDescriptionReply,
    PageDescriptionResponse,
    PageElement,
    PageSectionSummary,
)
from src.logger import get_logger, log_step

log = get_logger("accessibility.page_assistant")

_DEFAULTS: dict[str, Any] = {
    "provider_url": "https://openrouter.ai/api/v1",
    "api_key_env": "OPENROUTER_API_KEY",
    "model": "google/gemini-2.5-flash",
    "temperature": 0.2,
    "max_tokens": 4000,
    "reasoning": "off",          # off | low | medium | high | "" (model default). Thinking tokens count
                                 # against max_tokens; "off" measured ~2x faster with valid replies
    "timeout": 30,
    "max_page_chars": 12000,
}
_ACTION_KINDS = {"button": "button", "link": "link", "field": "field", "form": "form"}
_KIND_AR = {"button": "زر", "link": "رابط", "field": "حقل", "form": "نموذج"}
_SPEECH_PART_CHARS = 280            # browser speech engines cut very long utterances

SYSTEM_PROMPT = """You help blind and visually impaired Arabic speakers understand a webpage by voice.
You receive the visible content of ONE page as numbered lines, in reading order:
  <id> | <region> | <kind> [details] | <text>
Return JSON only, matching the schema. Write every sentence in clear, simple Modern Standard Arabic.

Rules:
- Use ONLY information present in the lines. Never invent features, numbers, names, steps or purposes.
  If something is not stated, leave it out (use "" for purpose when a button's effect is not clear).
- main_heading: copy the page's main heading text exactly (usually the h1).
- purpose: one short sentence, based on the headings and text.
- introduction: 2-3 short, natural spoken sentences: where the user is and what they can do here.
  Do not list every element; do not mention ids, regions, HTML or "the extracted content".
- sections: at most 6 main content sections in logical reading order (follow the headings of the main
  region); title copied from the page; summary = ONE short sentence from that section's text only.
  Skip header/footer/navigation.
- actions: at most 8 of the most important buttons, links, forms and fields for this page's purpose, in page order,
  with their exact label. Skip repeated site navigation unless the page has nothing else. Do not list long
  groups of similar controls one by one (e.g. calendar days, pagination numbers, rating stars).
- clarifications: only for an element whose label is unclear AND other text on the page explains it.
  Usually empty.
- Refer to elements by their id (e.g. "e12"). Use only ids that appear in the lines."""


def settings() -> dict[str, Any]:
    return {**_DEFAULTS, **(get_config().get("accessibility") or {})}


# ---------------------------------------------------------------- page -> prompt

def page_lines(page: PageContentRequest, max_chars: int) -> str:
    """The page as numbered lines for the LLM, cut at max_chars."""
    lines, used = [f"page title: {page.title}", f"page path: {page.url}"], 0
    for el in page.elements:
        details = el.kind
        if el.kind == "heading" and el.level:
            details += f" h{el.level}"
        if el.kind == "link" and el.href:
            details += f" {el.href}"
        if el.kind == "field" and el.field_type:
            details += f" {el.field_type}"
        if el.required:
            details += " required"
        if el.disabled:
            details += " disabled"
        line = f"{el.id} | {el.region} | {details} | {' '.join(el.text.split())}"
        used += len(line)
        if used > max_chars:
            lines.append("(the rest of the page was cut)")
            break
        lines.append(line)
    return "\n".join(lines)


# ---------------------------------------------------------------- JSON schema for the provider

def _strict_schema(model: type) -> dict:
    """Pydantic JSON schema -> self-contained strict schema (no $ref, all fields required, no extras).

    Length limits are left out of the request (not every provider accepts them); pydantic still checks them.
    """
    root = model.model_json_schema()
    defs = root.pop("$defs", {})
    drop = {"title", "default", "maxLength", "minLength", "maxItems", "minItems", "pattern"}

    def walk(node):
        if isinstance(node, dict):
            if "$ref" in node:
                return walk(defs[node["$ref"].split("/")[-1]])
            out = {k: walk(v) for k, v in node.items() if k not in drop}
            if out.get("type") == "object" and "properties" in out:
                out["required"] = list(out["properties"])
                out["additionalProperties"] = False
            return out
        if isinstance(node, list):
            return [walk(item) for item in node]
        return node

    return walk(root)


# ---------------------------------------------------------------- LLM call

class AssistantUnavailable(RuntimeError):
    """No key, network error, provider error or an invalid reply: the rule-based description is used."""


def _parse_json(content: str) -> dict:
    content = content.strip()
    fenced = re.match(r"^```(?:json)?\s*(.*?)\s*```$", content, re.S)
    return json.loads(fenced.group(1) if fenced else content)


def _limit(value: Any, field_info) -> Any:
    """Cut a too-long string or list to the field's max_length (never adds anything)."""
    limit = next((m.max_length for m in field_info.metadata if getattr(m, "max_length", None)), None)
    if limit is None:
        return value
    if isinstance(value, str) and len(value) > limit:
        cut = value[:limit]
        return cut.rsplit(" ", 1)[0] if " " in cut[limit // 2:] else cut
    if isinstance(value, list) and len(value) > limit:
        return value[:limit]
    return value


def trim_to_schema(data: Any, model: type = PageDescriptionResponse) -> Any:
    """Make a slightly too long LLM reply fit the schema limits before pydantic validates it."""
    if not isinstance(data, dict):
        return data
    out = dict(data)
    for name, info in model.model_fields.items():
        if name not in out:
            continue
        value = _limit(out[name], info)
        item_model = {"sections": PageSectionSummary, "actions": PageActionSummary,
                      "clarifications": PageClarification}.get(name) if model is PageDescriptionResponse else None
        if item_model and isinstance(value, list):
            value = [trim_to_schema(item, item_model) for item in value]
        out[name] = value
    return out


def _ask_llm(page: PageContentRequest, s: dict[str, Any]) -> PageDescriptionResponse:
    api_key = (get_secret(s["api_key_env"]) or "").strip()
    if not api_key:
        raise AssistantUnavailable(f"{s['api_key_env']} is not set")
    messages = [{"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": page_lines(page, int(s["max_page_chars"]))}]
    body: dict[str, Any] = {
        "model": s["model"],
        "temperature": s["temperature"],
        "max_tokens": s["max_tokens"],
        "response_format": {"type": "json_schema", "json_schema": {
            "name": "page_description", "strict": True, "schema": _strict_schema(PageDescriptionResponse)}},
    }
    reasoning = str(s.get("reasoning") or "").lower()
    if reasoning == "off":
        body["reasoning"] = {"enabled": False}
    elif reasoning:
        body["reasoning"] = {"effort": reasoning, "exclude": True}
    headers = {"Authorization": f"Bearer {api_key}"}
    url = f"{str(s['provider_url']).rstrip('/')}/chat/completions"
    with httpx.Client(timeout=float(s["timeout"])) as client:
        for attempt in (1, 2):
            try:
                response = client.post(url, headers=headers, json={**body, "messages": messages})
            except httpx.HTTPError as exc:
                raise AssistantUnavailable(f"network: {type(exc).__name__}") from exc
            if response.status_code != 200:
                raise AssistantUnavailable(f"HTTP {response.status_code}")
            content, finish, usage = "", None, {}
            try:
                data = response.json()
                finish, usage = data["choices"][0].get("finish_reason"), data.get("usage") or {}
                content = data["choices"][0]["message"]["content"] or ""
                return PageDescriptionResponse.model_validate(trim_to_schema(_parse_json(content)))
            except (KeyError, IndexError, TypeError, ValueError, ValidationError) as exc:
                log.warning("[WARN]  invalid LLM reply (attempt %d) -> %s (finish=%s, completion tokens=%s, reasoning=%s)",
                            attempt, type(exc).__name__, finish, usage.get("completion_tokens"),
                            (usage.get("completion_tokens_details") or {}).get("reasoning_tokens"))
                if attempt == 2:
                    raise AssistantUnavailable(f"invalid reply: {type(exc).__name__}") from exc
                problem = str(exc)[:500]
                messages = [*messages, {"role": "assistant", "content": content[:4000]},
                            {"role": "user", "content": f"That JSON was invalid ({problem}). Return valid JSON only."}]
    raise AssistantUnavailable("no reply")   # pragma: no cover


# ---------------------------------------------------------------- grounding (never read invented content)

def _norm(text: str) -> str:
    return " ".join(text.split())


def _state_note(el: PageElement, purpose: str) -> str:
    """Add the element's real state from the page (disabled, required) to what is read aloud."""
    notes = [n for n, on in (("غير متاح حاليًا", el.disabled), ("إلزامي", el.required and el.kind == "field")) if on]
    return "، ".join([p for p in (_norm(purpose), *notes) if p])


def ground(answer: PageDescriptionResponse, page: PageContentRequest) -> PageDescriptionResponse:
    """Keep only what refers to the extracted page; replace labels/titles with the page's own text."""
    by_id: dict[str, PageElement] = {el.id: el for el in page.elements}
    headings = [el for el in page.elements if el.kind == "heading" and el.text.strip()]
    heading_texts = {_norm(h.text) for h in headings}

    main_heading = _norm(answer.main_heading)
    if main_heading not in heading_texts and main_heading != _norm(page.title):
        first = next((h for h in headings if h.level == 1), headings[0] if headings else None)
        main_heading = _norm(first.text) if first else _norm(page.title) or main_heading

    sections = []
    for sec in answer.sections:
        el = by_id.get(sec.heading_id)
        if sec.heading_id and (el is None or el.kind != "heading"):
            continue                                   # refers to a heading that is not on the page
        title = _norm(el.text) if el else _norm(sec.title)
        if not title or (not el and title not in heading_texts):
            continue                                   # no heading of the page to name it
        sections.append(PageSectionSummary(heading_id=sec.heading_id, title=title[:150], summary=sec.summary))

    actions = []
    for act in answer.actions:
        el = by_id.get(act.element_id)
        if el is None or el.kind not in _ACTION_KINDS:
            continue
        label = _norm(el.text) or _norm(act.label)
        if not label:
            continue
        actions.append(PageActionSummary(element_id=el.id, kind=_ACTION_KINDS[el.kind],
                                         label=label[:150], purpose=_state_note(el, act.purpose)[:250]))

    clarifications = [c for c in answer.clarifications if c.element_id in by_id]
    dropped = (len(answer.sections) - len(sections) + len(answer.actions) - len(actions)
               + len(answer.clarifications) - len(clarifications))
    if dropped:
        log.info("[CHECK] dropped %d item(s) not found on the page", dropped)
    return PageDescriptionResponse(purpose=answer.purpose, main_heading=main_heading[:200] or "الصفحة",
                                   introduction=answer.introduction, sections=sections,
                                   actions=actions, clarifications=clarifications)


# ---------------------------------------------------------------- fallback without the LLM

def rules_description(page: PageContentRequest) -> PageDescriptionResponse:
    """Headings, their first text and the main controls, read straight from the page."""
    main = [el for el in page.elements if el.region in ("main", "dialog")] or list(page.elements)
    headings = [el for el in main if el.kind == "heading" and el.text.strip()]
    h1 = next((h for h in headings if h.level == 1), headings[0] if headings else None)
    main_heading = _norm(h1.text) if h1 else _norm(page.title) or "الصفحة"

    sections = []
    for i, el in enumerate(main):
        if el.kind != "heading" or el is h1 or not el.text.strip():
            continue
        following = next((n for n in main[i + 1:] if n.kind in ("text", "heading")), None)
        summary = _norm(following.text)[:300] if following and following.kind == "text" else ""
        sections.append(PageSectionSummary(heading_id=el.id, title=_norm(el.text)[:150], summary=summary))
        if len(sections) == 8:
            break

    actions = [PageActionSummary(element_id=el.id, kind=_ACTION_KINDS[el.kind], label=_norm(el.text)[:150],
                                 purpose=_state_note(el, ""))
               for el in main if el.kind in ("button", "link", "field") and el.text.strip() and not el.disabled][:10]
    first_text = next((_norm(el.text) for el in main if el.kind == "text" and len(el.text.strip()) > 20), "")
    intro = f"أنت في صفحة {main_heading}."
    if first_text:
        intro += f" {first_text[:250]}"
    return PageDescriptionResponse(purpose="", main_heading=main_heading[:200], introduction=intro[:450],
                                   sections=sections, actions=actions, clarifications=[])


# ---------------------------------------------------------------- text to read aloud

def _split(text: str) -> list[str]:
    """Cut long text at sentence ends so each spoken part stays short."""
    parts, current = [], ""
    for sentence in re.split(r"(?<=[.!؟?،])\s+", _norm(text)):
        if current and len(current) + len(sentence) + 1 > _SPEECH_PART_CHARS:
            parts.append(current)
            current = sentence
        else:
            current = f"{current} {sentence}".strip()
    if current:
        parts.append(current)
    return parts


def _sentence(*pieces: str) -> str:
    """Join pieces into one spoken sentence without doubled punctuation ("؟." -> "؟")."""
    text = ""
    for piece in (p.strip() for p in pieces if p and p.strip()):
        text = f"{text}{'' if not text else ('' if text[-1] in '.!؟?،:' else '.')} {piece}".strip()
    return text if not text or text[-1] in ".!؟?" else f"{text}."


def speech_parts(d: PageDescriptionResponse) -> list[str]:
    """Arabic text for the existing browser TTS, built only from validated, grounded fields."""
    parts = _split(d.introduction)
    if d.sections:
        parts.append(f"تحتوي الصفحة على {len(d.sections)} أقسام بالترتيب التالي." if len(d.sections) > 2
                     else "أقسام الصفحة:")
        for sec in d.sections:
            parts += _split(_sentence(sec.title, sec.summary))
    if d.actions:
        parts.append("أهم ما يمكنك فعله في هذه الصفحة:")
        for act in d.actions:
            parts += _split(_sentence(f"{_KIND_AR[act.kind]} {act.label}" + (f"، {act.purpose}" if act.purpose else "")))
    for c in d.clarifications:
        parts += _split(f"توضيح: {c.explanation}")
    return [p for p in parts if p.strip()]


# ---------------------------------------------------------------- entry point

@log_step(summary=lambda r: f"via={r.via}, {len(r.description.sections)} sections, "
                            f"{len(r.description.actions)} actions, {len(r.speech)} speech parts")
def describe_page(page: PageContentRequest) -> PageDescriptionReply:
    """Validated Arabic description of the page + the parts to read aloud. Never raises for LLM problems."""
    s = settings()
    log.info("[INPUT] page %s: %d elements", page.url[:80], len(page.elements))
    try:
        description, via, model = ground(_ask_llm(page, s), page), "llm", s["model"]
    except AssistantUnavailable as exc:
        log.warning("[FALLBACK] accessibility assistant -> rules (%s)", exc)
        description, via, model = rules_description(page), "rules", None
    return PageDescriptionReply(via=via, model=model, description=description, speech=speech_parts(description))
