"""Shared types for Sanad: enums, Claude response models and WebSocket messages.

One place for every value that crosses a boundary:
    - Enums            used by the agents, the API and the database
    - LLM responses    what Claude must return (validated with pydantic, never parsed by hand)
    - Client messages  what the browser may send on WS /interview/{session} and POST /accessibility/describe
    - Server messages  what the API sends back

The enums subclass str, so `Mode.AI == "ai"` and they serialise to JSON as plain strings.
"""
from __future__ import annotations

from enum import Enum
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator


# ------------------------------------------------------------------ enums

class Mode(str, Enum):
    """How the interview is translated. Case 1 = human, Case 2 = ai, Case 3 = ai -> human."""
    HUMAN = "human"
    AI = "ai"


class EventType(str, Enum):
    QUESTION = "question"         # the recruiter spoke
    SIGNS = "signs"               # the candidate signed
    CHOOSE = "choose"             # the candidate picked an option or "None of these"
    INTERPRETER = "interpreter"   # the "I need an interpreter" button


class InterpreterReason(str, Enum):
    BUTTON = "button"             # the candidate pressed the button
    NONE_LIMIT = "none_limit"     # "None of these" reached interview_agent.max_none_of_these


class Notice(str, Enum):
    """Why an interview event did not change anything (sent instead of an error)."""
    HUMAN_MODE = "human_mode"                           # signs/choices ignored: a human interprets
    INVALID_CHOICE = "invalid_choice"                   # option index out of range
    NO_SIGNS_RECOGNIZED = "no_signs_recognized"         # no words -> sign again
    INTERPRETER_ALREADY_CALLED = "interpreter_already_called"
    UNKNOWN_EVENT = "unknown_event"


class MissingField(str, Enum):
    """CV details the Job Agent must ask the candidate for."""
    SKILLS = "skills"
    CITY = "city"


# ------------------------------------------------------------------ Claude responses
# Passed to llm.with_structured_output(...): Claude must fill these fields and pydantic checks them.

class CvProfileResponse(BaseModel):
    """The candidate profile found in a CV."""
    skills: list[str] = Field(default_factory=list, description="Short skill names mentioned in the CV")
    major: str | None = Field(default=None, description="Field of study, or null if not stated")
    experience_years: float | None = Field(default=None, ge=0, le=60,
                                           description="Total years of work experience, or null if not stated")
    city: str | None = Field(default=None, description="City where the candidate lives, or null if not stated")


class JobScoreResponse(BaseModel):
    """How well one job fits the candidate."""
    match: int = Field(ge=0, le=100, description="Match percentage 0-100")
    reason: str = Field(min_length=3, max_length=300, description="One short sentence in simple Arabic explaining the match")


class SentenceOptionsResponse(BaseModel):
    """Answer options built from the recognised sign words."""
    options: list[str] = Field(min_length=1, max_length=5,
                               description="Short, polite Modern Standard Arabic answers, best first")


class PageSectionSummary(BaseModel):
    """One section of a webpage, in reading order."""
    # Defaults: some models leave a field out; titles and labels are replaced with the page's own text anyway.
    heading_id: str = Field(default="", max_length=8, description='id of the heading element that starts the section (e.g. "e4"), or "" if none')
    title: str = Field(default="", max_length=150, description="The section name as written on the page")
    summary: str = Field(default="", max_length=350, description="One or two short Arabic sentences using only text from this section")


class PageActionSummary(BaseModel):
    """An important button, link, form or field and what it does."""
    element_id: str = Field(max_length=8, description='id of the element in the extracted page (e.g. "e12")')
    kind: Literal["button", "link", "form", "field"]
    label: str = Field(default="", max_length=150, description="The element's label exactly as on the page")
    purpose: str = Field(default="", max_length=250, description="What it does in short Arabic, only if the page states it or its label makes it clear; otherwise empty")


class PageClarification(BaseModel):
    """An explanation of an unclear element, only when the page itself supports it."""
    element_id: str = Field(max_length=8, description="id of the unclear element")
    explanation: str = Field(min_length=3, max_length=300, description="Short Arabic explanation based only on information on the page")


class PageDescriptionResponse(BaseModel):
    """What a blind user should hear about the current webpage (web accessibility assistant)."""
    purpose: str = Field(max_length=300, description="The page's purpose in one short Arabic sentence, from its content only")
    main_heading: str = Field(min_length=1, max_length=200, description="The page's main heading exactly as written on the page")
    introduction: str = Field(min_length=10, max_length=450, description="A short, natural spoken Arabic introduction to the page (2-3 sentences)")
    sections: list[PageSectionSummary] = Field(default_factory=list, max_length=12, description="Sections in logical reading order")
    actions: list[PageActionSummary] = Field(default_factory=list, max_length=15, description="The most important buttons, links, forms and fields, in page order")
    clarifications: list[PageClarification] = Field(default_factory=list, max_length=8, description="Only for unclear elements the page explains elsewhere; usually empty")


# ------------------------------------------------------------------ browser -> API (WebSocket)

class _ClientMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")   # unknown fields are a mistake in the client


Point = Annotated[list[float], Field(min_length=2, max_length=3)]     # [x, y] or [x, y, z]
Frame = Annotated[list[Point], Field(min_length=1)]                   # 42 points: left hand + right hand
Segment = Annotated[list[Frame], Field(min_length=1)]                 # one sign


class StartMessage(_ClientMessage):
    type: Literal["start"]
    mode: Mode
    job_id: str | None = None
    candidate_id: int | None = None


class QuestionMessage(_ClientMessage):
    type: Literal["question"]
    text: str | None = Field(default=None, max_length=2000)
    audio_b64: str | None = None
    segments: list[Segment] | None = None   # optional: signs sent together with the question

    @model_validator(mode="after")
    def _text_or_audio(self):
        if not (self.text and self.text.strip()) and not self.audio_b64:
            raise ValueError("a question needs 'text' or 'audio_b64'")
        return self


class SignsMessage(_ClientMessage):
    type: Literal["signs"]
    segments: list[Segment] = Field(min_length=1, max_length=20)


class ChooseMessage(_ClientMessage):
    type: Literal["choose"]
    index: int | None = Field(ge=0, le=9, description="0-based option, or null for 'None of these'")


class InterpreterMessage(_ClientMessage):
    type: Literal["interpreter"]


EventMessage = Annotated[Union[QuestionMessage, SignsMessage, ChooseMessage, InterpreterMessage],
                         Field(discriminator="type")]
event_message_adapter: TypeAdapter[EventMessage] = TypeAdapter(EventMessage)


# ------------------------------------------------------------------ browser -> API (POST /accessibility/describe)

PageElementKind = Literal["heading", "text", "button", "link", "field", "form", "image"]
PageRegion = Literal["header", "nav", "main", "aside", "footer", "dialog", "other"]


class PageElement(_ClientMessage):
    """One visible element of the current page, in DOM (reading) order, as extracted by the browser."""
    id: str = Field(pattern=r"^e\d{1,4}$")
    kind: PageElementKind
    text: str = Field(default="", max_length=400)            # visible text or accessible name
    level: int | None = Field(default=None, ge=1, le=6)      # headings
    region: PageRegion = "main"
    href: str | None = Field(default=None, max_length=300)   # links (path only)
    field_type: str | None = Field(default=None, max_length=30)
    required: bool | None = None
    disabled: bool | None = None


class PageContentRequest(_ClientMessage):
    """The extracted content of the page the user is on."""
    url: str = Field(max_length=500)
    title: str = Field(default="", max_length=200)
    elements: list[PageElement] = Field(min_length=1, max_length=400)


# ------------------------------------------------------------------ API -> browser (WebSocket)

class StartedReply(BaseModel):
    type: Literal["started"] = "started"
    interview_id: int
    mode: Mode


class StateReply(BaseModel):
    type: Literal["state"] = "state"
    mode: Mode
    last_question: str | None = None
    sentence_options: list[str] = Field(default_factory=list)
    chosen_sentence: str | None = None
    none_count: int = 0
    interpreter_called: bool = False
    interpreter: dict | None = None
    notice: Notice | None = None


class ErrorReply(BaseModel):
    type: Literal["error"] = "error"
    error: str                                          # "invalid_message" or an exception name
    details: list[str] = Field(default_factory=list)    # what was wrong with the message


# ------------------------------------------------------------------ API -> browser (HTTP)

class PageDescriptionReply(BaseModel):
    """POST /accessibility/describe: the validated description and the text to read aloud."""
    via: Literal["llm", "rules"]                           # rules = fallback without the LLM
    model: str | None = None
    description: PageDescriptionResponse
    speech: list[str]                                      # short Arabic parts, read aloud in order
