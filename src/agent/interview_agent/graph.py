"""Interview Agent graph — the three cases.

Case 1 (human from the start): speech_to_text only; the human interpreter conveys signs.
Case 2 (AI only): speech_to_text || recognize_sign (parallel) -> compose_sentence
        -> candidate picks option 1/2/3 (sent to recruiter) or "None of these" (sign again).
Case 3 (switch to human): "I need an interpreter" button at any moment (immediate),
        or "None of these" reaches interview_agent.max_none_of_these (forced)
        -> call_interpreter -> continue as Case 1.

The graph runs once per event; state is kept per session by the checkpointer
(thread_id = session_id). Use InterviewSession for a simple API.
"""
from __future__ import annotations

import time

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from src.agent.core.config import get_config
from src.logger import get_logger

from src.agent.schemas import EventType, InterpreterReason, Mode, Notice

from .state import InterviewEvent, InterviewState
from .tools.call_interpreter import call_interpreter
from .tools.compose_sentence import compose_sentence
from .tools.recognize_sign import recognize_sign
from .tools.speech_to_text import speech_to_text

log = get_logger("interview_agent")


def _settings() -> dict:
    return get_config()["interview_agent"]


def receive_node(state: InterviewState) -> dict:
    """Clear the per-event outputs of the previous run."""
    return {"chosen_sentence": None, "interpreter": None, "notice": None}


def route_event(state: InterviewState) -> list[str] | str:
    event = state.get("event") or {}
    kind = event.get("type")
    human = state.get("mode") == Mode.HUMAN
    if kind == EventType.INTERPRETER:
        log.info("[DECISION] interpreter button -> call_interpreter")
        return "call_interpreter"
    nodes = []
    if kind == EventType.QUESTION or event.get("text") or event.get("audio"):
        nodes.append("speech_to_text")
    if kind == EventType.SIGNS or event.get("segments"):
        nodes.append("ignore" if human else "recognize_sign")
    if kind == EventType.CHOOSE:
        nodes.append("ignore" if human else "choose")
    if not nodes:
        nodes = ["ignore"]
    log.info("[DECISION] event '%s' in %s mode -> %s", kind, state.get("mode"), " + ".join(nodes))
    return nodes if len(nodes) > 1 else nodes[0]


def speech_node(state: InterviewState) -> dict:
    event = state["event"]
    question = speech_to_text(event.get("audio") if event.get("audio") else event.get("text", ""))
    return {"last_question": question}


def recognize_node(state: InterviewState) -> dict:
    return {"candidate_words": recognize_sign(state["event"].get("segments", []))}


def compose_node(state: InterviewState) -> dict:
    options = compose_sentence(state.get("candidate_words", []), state.get("last_question", ""))
    if not options:
        log.warning("[RESULT] no options -> candidate is asked to sign again")
        return {"sentence_options": [], "notice": Notice.NO_SIGNS_RECOGNIZED}
    return {"sentence_options": options}


def choose_node(state: InterviewState) -> dict:
    index = state["event"].get("index")
    options = state.get("sentence_options", [])
    if index is not None:
        if not 0 <= index < len(options):
            log.warning("[WARN] choice %s is not one of %d options -> ignored", index, len(options))
            return {"notice": Notice.INVALID_CHOICE}
        log.info("[RESULT] candidate chose option %d -> sent to recruiter", index + 1)
        update: dict = {"chosen_sentence": options[index], "sentence_options": []}
        if _settings().get("none_counter") == "consecutive":
            update["none_count"] = 0
        return update
    count = state.get("none_count", 0) + 1
    log.info("[RESULT] 'None of these' -> count %d of %d (%s)", count, _settings()["max_none_of_these"],
             _settings().get("none_counter", "total"))
    return {"none_count": count, "sentence_options": []}


def after_choose(state: InterviewState) -> str:
    event = state["event"]
    if event.get("index") is None and state.get("none_count", 0) >= _settings()["max_none_of_these"]:
        log.info("[DECISION] 'None of these' limit reached -> forced switch to human interpreter")
        return "call_interpreter"
    return END


def interpreter_node(state: InterviewState) -> dict:
    if state.get("interpreter_called"):
        log.info("[RESULT] interpreter already in the call -> nothing to do")
        return {"notice": Notice.INTERPRETER_ALREADY_CALLED}
    reason = (InterpreterReason.BUTTON if state["event"].get("type") == EventType.INTERPRETER
              else InterpreterReason.NONE_LIMIT)
    result = call_interpreter(state.get("session_id", ""), reason)
    log.info("[RESULT] mode ai -> human (interpreter joined, reason=%s)", reason.value)
    return {"interpreter": result, "interpreter_called": True, "mode": Mode.HUMAN, "sentence_options": []}


def ignore_node(state: InterviewState) -> dict:
    kind = (state.get("event") or {}).get("type")
    log.warning("[RESULT] event '%s' ignored (%s mode)", kind, state.get("mode"))
    human_only = state.get("mode") == Mode.HUMAN and kind in (EventType.SIGNS, EventType.CHOOSE)
    return {"notice": Notice.HUMAN_MODE if human_only else Notice.UNKNOWN_EVENT}


def build_interview_graph(checkpointer=None):
    """Build and compile the LangGraph StateGraph for the Interview Agent."""
    graph = StateGraph(InterviewState)
    graph.add_node("receive", receive_node)
    graph.add_node("speech_to_text", speech_node)
    graph.add_node("recognize_sign", recognize_node)
    graph.add_node("compose_sentence", compose_node)
    graph.add_node("choose", choose_node)
    graph.add_node("call_interpreter", interpreter_node)
    graph.add_node("ignore", ignore_node)

    graph.add_edge(START, "receive")
    graph.add_conditional_edges(
        "receive", route_event, ["speech_to_text", "recognize_sign", "choose", "call_interpreter", "ignore"])
    graph.add_edge("speech_to_text", END)
    graph.add_edge("recognize_sign", "compose_sentence")
    graph.add_edge("compose_sentence", END)
    graph.add_conditional_edges("choose", after_choose, ["call_interpreter", END])
    graph.add_edge("call_interpreter", END)
    graph.add_edge("ignore", END)
    return graph.compile(checkpointer=checkpointer or MemorySaver())


_OUTPUT_KEYS = ("mode", "last_question", "sentence_options", "chosen_sentence", "none_count",
                "interpreter_called", "interpreter", "notice")


class InterviewSession:
    """One interview: start with a mode, then send events and get the visible state back."""

    def __init__(self, session_id: str, mode: Mode | str, graph=None):
        mode = Mode(mode)   # raises ValueError for anything but "human" / "ai"
        self.session_id = session_id
        self.graph = graph or build_interview_graph()
        self._config = {"configurable": {"thread_id": session_id}}
        # Sent with the first event (the checkpointer has no state for this thread yet).
        self._initial: dict | None = {
            "session_id": session_id, "mode": mode, "none_count": 0,
            "interpreter_called": False, "sentence_options": []}
        log.info("[RUN] interview started: session=%s mode=%s", session_id, mode.value)

    def send(self, event: InterviewEvent) -> dict:
        payload = {**(self._initial or {}), "event": event}
        self._initial = None
        log.info("[EVENT] session=%s received '%s'", self.session_id, event.get("type"))
        started = time.perf_counter()
        try:
            state = self.graph.invoke(payload, self._config)
        except Exception as exc:
            log.error("[FAIL]  event '%s' -> %s: %s", event.get("type"), type(exc).__name__, exc)
            raise
        log.info("[DONE] event '%s' handled in %.0f ms -> mode=%s none_count=%s options=%d",
                 event.get("type"), (time.perf_counter() - started) * 1000, state.get("mode"),
                 state.get("none_count"), len(state.get("sentence_options") or []))
        return {key: state.get(key) for key in _OUTPUT_KEYS}
