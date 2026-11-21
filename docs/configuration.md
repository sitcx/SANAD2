# Configuration

Two places: **`config.yaml`** for settings (in git) and **`.env`** for secrets and machine-specific
values (not in git; copy from `.env.example`).

## config.yaml

| Key | Default | Meaning |
|---|---|---|
| `llm.model` | `claude-sonnet-5-5` | Claude model used by the agents |
| `job_agent.recommended_jobs` | `3` | how many jobs are marked "recommended" |
| `job_agent.min_matches` | `3` | fewer matches than this → widen the search |
| `job_agent.jobs_file` | `src/data/jobs.json` | the job catalogue |
| `interview_agent.sentence_options` | `3` | sentence options shown to the candidate (plus "None of these") |
| `interview_agent.max_none_of_these` | `5` | "None of these" count that forces a human interpreter |
| `interview_agent.none_counter` | `total` | `total` = whole interview, `consecutive` = resets when an option is chosen |
| `interview_agent.interpreter_button` | `true` | "I need an interpreter" button always visible |
| `signs.dataset_dir` | `src/data/dataset` | Saudi Sign Language dataset |
| `signs.vocabulary_size` | `40` | target number of gallery words |
| `signs.gallery_dir` | `src/data/sign_gallery` | sign gallery |
| `accessibility.provider_url` | `https://openrouter.ai/api/v1` | OpenAI-compatible chat API for the web accessibility assistant |
| `accessibility.api_key_env` | `OPENROUTER_API_KEY` | name of the key in `.env` (server only) |
| `accessibility.model` | `google/gemini-2.5-flash` | model that describes pages |
| `accessibility.reasoning` | `"off"` | `off` · `low` · `medium` · `high` · `""` (model default); off was ~2× faster |
| `accessibility.max_tokens` / `timeout` / `max_page_chars` | `4000` / `30` / `12000` | reply size, seconds, longest page text sent |
| `database.path` | `instance/sanad.db` | SQLite file |
| `logging.level` | `INFO` | log level |
| `logging.file` | `src/logger/logs/sanad.log` | log file |

Restart the API after changing `config.yaml` (`run.py` restarts it automatically when files in `src/` change, but not for `config.yaml`).

## .env

| Variable | Side | Meaning |
|---|---|---|
| `ANTHROPIC_API_KEY` | server | enables Claude; empty = rule-based fallbacks |
| `OPENROUTER_API_KEY` | server | web accessibility assistant (page descriptions); empty = rule-based description |
| `VITE_SANAD_API_URL` | browser (public) | API address used by the web UI; default `http://localhost:8010` |
| `SANAD_API_PORT` | launcher | port `run.py` starts the API on; default `8010` |
| `SANAD_WEB_ORIGINS` | server | browser origins allowed to call the API (comma-separated) |
| `SANAD_LOG_FILE` | server | log file path; `none` = console only; empty = `config.yaml` value |
| `SIGN_DATASET_DIR` | server | dataset location if not in `src/data/dataset` |

Anything starting with `VITE_` is visible in the browser: never put secrets there.
An empty value (`NAME=`) means "use the default". The optional variables are commented out in `.env.example`.

## Jobs

Edit `src/data/jobs.json`. Each job:

```json
{
  "id": "analyst",
  "title": "Data Analyst",
  "title_ar": "محلل بيانات",
  "company": "Buad Tech",
  "city": "Riyadh",
  "mode": "Hybrid",
  "description": "…",
  "skills": ["Excel", "SQL", "Data analysis"],
  "skills_ar": {"Data analysis": "تحليل البيانات"}
}
```

The web UI shows its own job cards from `src/web/lib/sanad-data.ts`; keep the `id`s the same in both files.
