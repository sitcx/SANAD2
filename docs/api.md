# API reference

Base URL: `http://localhost:8010` · interactive docs at `/docs` · every response has an
`X-Sanad-Run-Id` header that matches the request id in the log.

Allowed browser origins: `SANAD_WEB_ORIGINS` (default `http://localhost:3000`).

## `GET /health`

```json
{"status": "ok"}
```

## `POST /accessibility/describe`

Web accessibility assistant: a short Arabic spoken guide to the page the user is on (blind and visually
impaired users, voice mode). Body (`PageContentRequest`): the page's visible elements in reading order.

```json
{"url": "/jobs", "title": "الوظائف", "elements": [
  {"id": "e1", "kind": "heading", "level": 1, "region": "main", "text": "الوظائف"},
  {"id": "e2", "kind": "button", "region": "main", "text": "تقديم", "disabled": true}
]}
```

`kind`: `heading` `text` `button` `link` `field` `form` `image` · `region`: `header` `nav` `main` `aside` `footer` `dialog` `other`.

Reply (`PageDescriptionReply`): `via` (`llm` or `rules` fallback), `model`, `description`
(`PageDescriptionResponse`: purpose, main_heading, introduction, sections, actions, clarifications) and
`speech` (short Arabic parts to read aloud in order). The LLM reply is validated with pydantic and grounded:
anything that refers to an element not in the request is dropped, and labels come from the page.

## `POST /jobs/recommend`

Runs the Job Agent. Body is `multipart/form-data`:

| Field | Required | Description |
|---|---|---|
| `cv` | one of `cv` / `profile` | CV file: `.pdf`, `.docx`, `.txt`, `.md`, `.json`; max 10 MB |
| `profile` | one of `cv` / `profile` | JSON profile instead of a file: `{"skills": [...], "city": "..."}` |
| `answers` | no | JSON with the candidate's answers to `missing_info`, e.g. `{"city": "الرياض"}` |
| `name` | no | candidate name stored in the database |

**The agent needs more information:**

```json
{
  "status": "need_info",
  "missing_info": ["city"],
  "profile": {"skills": ["excel", "sql"], "major": null, "experience_years": 2.0, "city": null}
}
```

Send the same request again with `answers`.

**Success:**

```json
{
  "status": "ok",
  "candidate_id": 2,
  "profile": {"skills": ["excel", "sql"], "major": null, "experience_years": 2.0, "city": "الرياض"},
  "widened": true,
  "jobs": [
    {"id": "analyst", "title": "Data Analyst", "title_ar": "محلل بيانات", "city": "Riyadh",
     "job_id": "analyst", "match": 73, "reason": "مهاراتك في Excel، SQL تناسب متطلبات وظيفة محلل بيانات.",
     "matched_skills": ["Excel", "SQL"], "via": "rules"}
  ],
  "recommended": ["… first job_agent.recommended_jobs items of jobs …"]
}
```

`jobs` is sorted by `match` (highest first). `widened` is `true` when the search was widened.

**Errors:** `413` file larger than 10 MB · `415` unsupported file type · `422` missing CV/profile or invalid JSON.

Example:

```bash
curl -F "cv=@cv.pdf" -F 'answers={"city":"Riyadh"}' http://localhost:8010/jobs/recommend
```

## `WS /interview/{session_id}`

JSON messages in both directions.

**1. Start** (first message):

```json
{"type": "start", "mode": "ai", "job_id": "analyst", "candidate_id": 2}
```

Reply: `{"type": "started", "interview_id": 5, "mode": "ai"}`

**2. Events:**

| Message | Meaning |
|---|---|
| `{"type": "question", "text": "حدثنا عن خبرتك"}` | recruiter's words (from the browser's speech recognition) |
| `{"type": "question", "audio_b64": "..."}` | recruiter's audio instead of text (needs `faster-whisper`) |
| `{"type": "signs", "segments": [[[[x, y], ...], ...], ...]}` | candidate's signs; see [keypoint format](sign-recognition.md#keypoint-format) |
| `{"type": "choose", "index": 0}` | candidate picked option 1 (0-based) |
| `{"type": "choose", "index": null}` | "None of these" |
| `{"type": "interpreter"}` | "I need an interpreter" button |

**3. Reply to every event:**

```json
{
  "type": "state",
  "mode": "ai",
  "last_question": "حدثنا عن خبرتك",
  "sentence_options": ["...", "...", "..."],
  "chosen_sentence": null,
  "none_count": 0,
  "interpreter_called": false,
  "interpreter": null,
  "notice": null
}
```

- `chosen_sentence` is set only on the event where the candidate picked an option: show it to the recruiter.
- `interpreter` is set on the event that brought the interpreter in; it contains `reason` and display
  `steps` (`connecting` → `joined`, with Arabic messages).
- `notice` explains an ignored event (see [Agents](agents.md#interview-agent--srcagentinterview_agent)).
- A message that does not match the protocol gets
  `{"type": "error", "error": "invalid_message", "details": ["index: Input should be a valid integer"]}`
  and the interview continues. Unknown fields are rejected too.
- On a server error the reply is `{"type": "error", "error": "<ExceptionName>", "details": []}` and the interview continues.
- Every message is validated with the models in `src/agent/schemas.py` (`StartMessage`, `EventMessage`,
  `StartedReply`, `StateReply`, `ErrorReply`).
