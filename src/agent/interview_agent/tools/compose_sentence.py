"""Tool: compose_sentence — turns the words into 3 Arabic sentence options.

Uses the recruiter's last question so the options fit the question.
The UI adds a 4th choice: "None of these".
"""
from __future__ import annotations

import itertools
import json

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from src.agent.core.config import get_config
from src.agent.inference.llm import ask_claude, llm_available
from src.agent.schemas import SentenceOptionsResponse
from src.logger import get_logger, log_step

log = get_logger("interview_agent.compose_sentence")


class ComposeSentenceInput(BaseModel):
    """Parameters of compose_sentence."""
    candidate_words: list[list[dict]] = Field(
        description="From recognize_sign: per sign, a list of {label_ar, score} best first")
    last_question: str = Field(description="The recruiter's last question, so the answers fit it")


_PROMPT = """A deaf job candidate answered an interview question in Saudi Sign Language.
Sign recognition gave these candidate words, one list per sign, best guess first (with confidence):
{words}

Recruiter's question: {question}

Write {n} different short answers in clear, polite Modern Standard Arabic that the candidate most
likely meant. Use the recognized words (prefer high-confidence ones), keep the signs' order, and
answer the question. Do not add facts the words do not support."""


def _template_options(candidate_words: list[list[dict]], n: int) -> list[str]:
    """No LLM: join the words, trying the next-best word for each sign to make variants."""
    choices = [[w["label_ar"] for w in sign[:3]] for sign in candidate_words if sign]
    if not choices:
        return []
    options: list[str] = []
    for combo in itertools.islice(itertools.product(*choices), 50):
        sentence = " ".join(combo)
        if sentence not in options:
            options.append(sentence)
        if len(options) == n:
            break
    return options


@log_step(summary=lambda options: f"{len(options)} options")
def compose_sentence(candidate_words: list[list[dict]], last_question: str) -> list[str]:
    """Return interview_agent.sentence_options Arabic sentences (fewer, or none, if few words)."""
    n = get_config()["interview_agent"]["sentence_options"]
    if not any(candidate_words):
        log.warning("[WARN] no recognized words -> no options")
        return []
    if llm_available():
        try:
            words = json.dumps([[{"word": w["label_ar"], "score": w["score"]} for w in sign[:5]]
                                for sign in candidate_words], ensure_ascii=False)
            reply = ask_claude(_PROMPT.format(words=words, question=last_question or "(none)", n=n),
                               SentenceOptionsResponse)
            options = [o.strip() for o in reply.options if o.strip()]
            if options:
                log.info("[LLM] options written by Claude (validated)")
                return options[:n]
            log.warning("[FALLBACK] Claude returned no options -> word templates")
        except Exception as exc:  # noqa: BLE001 - fall back to templates
            log.warning("[FALLBACK] Claude failed (%s) -> word templates", type(exc).__name__)
    else:
        log.info("[FALLBACK] no ANTHROPIC_API_KEY -> word templates")
    return _template_options(candidate_words, n)


compose_sentence_tool = StructuredTool.from_function(
    compose_sentence, name="compose_sentence", args_schema=ComposeSentenceInput,
    description="Turn recognized sign words into short Arabic answer options that fit the recruiter's question.")
