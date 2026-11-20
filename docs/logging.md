# Logging

Logs go to the console (prefixed `[api]` when started with `run.py`) and to `src/logger/logs/sanad.log` (UTF-8).

## Line format

```
12:44:35 | INFO    | req-a5e3  | job_agent.score_job                | [OK]    score_job (1 ms) -> job=analyst match=73% via=rules
  time      level     run id      component                            message
```

- **Run id**: one per HTTP request (`req-xxxx`) or interview session (`int-xxxxx`). Filter by it to
  follow one request end to end. The same id is returned in the `X-Sanad-Run-Id` response header.
- **Component**: where the line comes from, e.g. `job_agent.read_cv`, `interview_agent`, `database.db`, `api`.

## Tags

| Tag | Meaning |
|---|---|
| `[REQUEST]` / `[RESPONSE]` | API request received / answered, with status code and duration |
| `[RUN]` / `[DONE]` | an agent run started / finished, with duration and outcome |
| `[START]` / `[OK]` / `[FAIL]` | one step (tool or database function) started / succeeded / failed — with duration and a short result, or the error |
| `[INPUT]` | what a step received (counts and types only) |
| `[DECISION]` | which branch the graph took and why |
| `[RESULT]` | outcome of a decision (chosen option, counter, mode switch) |
| `[LLM]` / `[FALLBACK]` | Claude was used / rules were used instead (and why) |
| `[EVENT]` | an interview event arrived |
| `[WARN]` / `[SKIP]` | something unusual that did not stop the run |

## Example: one CV request

```
req-a5e3 | api                 | [REQUEST] POST /jobs/recommend
req-a5e3 | job_agent           | [RUN] Job Agent started (from CV file)
req-a5e3 | job_agent.read_cv   | [FALLBACK] no ANTHROPIC_API_KEY -> keyword rules
req-a5e3 | job_agent.read_cv   | [OK]    read_cv (19 ms) -> skills=2 major=no years=2.0 city=none
req-a5e3 | job_agent           | [INPUT] candidate answered: ['city']
req-a5e3 | job_agent           | [DECISION] 1 jobs < min_matches 3 -> widen search
req-a5e3 | job_agent.score_job | [OK]    score_job (1 ms) -> job=analyst match=73% via=rules
req-a5e3 | job_agent           | [DONE] Job Agent finished in 51 ms -> 2 recommended
req-a5e3 | database.db         | [OK]    save_candidate (9 ms) -> candidate_id=2
req-a5e3 | api                 | [RESPONSE] POST /jobs/recommend -> 200 in 71 ms
```

## Finding problems quickly

```bash
findstr "[FAIL]" src\logger\logs\sanad.log   # Windows
grep -F "[FAIL]" src/logger/logs/sanad.log     # macOS / Linux / Git Bash
findstr "req-a5e3" src\logger\logs\sanad.log # one request
```

## Privacy

Never log CV text, names or answers. Summaries contain counts, ids and scores only.

## Adding logging to new code

```python
from src.logger import get_logger, log_step

log = get_logger("job_agent.my_tool")

@log_step(summary=lambda result: f"{len(result)} items")   # logs [START], [OK] (ms) -> summary, or [FAIL]
def my_tool(...):
    log.info("[DECISION] ...")
```

Then add the function to `LOGGED_FUNCTIONS` in `src/agent/tests/test_logging.py`; the test fails
for any listed function without `@log_step`.

## Settings

`config.yaml` → `logging.level` (`INFO`, `DEBUG`, …) and `logging.file`.
`SANAD_LOG_FILE=none` in `.env` logs to the console only.
