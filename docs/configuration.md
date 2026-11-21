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
| `speech.whisper_model` | `large-v3` | Whisper model for the interview microphone; the language is fixed to Arabic in code |
| `speech.device` | `auto` | `auto` = GPU if it works, otherwise CPU · `cpu` · `cuda` |
| `speech.compute_type` | `auto` | `int8_float16` on GPU, `int8` on CPU |
| `speech.beam_size` | `5` | Whisper beam search width (lower = faster, less accurate) |
| `speech.max_seconds` | `120` | longest accepted recording |
| `speech.min_arabic_ratio` | `0.5` | transcripts with a smaller share of Arabic-script words are rejected as non-Arabic |
| `speech.reject_other_languages` | `true` | reject a recording whose spoken language is clearly not Arabic (`other_language_min_prob` 0.5, `arabic_max_prob_to_reject` 0.2) |
| `database.path` | `instance/sanad.db` | SQLite file |
| `logging.level` | `INFO` | log level |
| `logging.file` | `src/logger/logs/sanad.log` | log file |

Restart the API after changing `config.yaml` (`run.py` restarts it automatically when files in `src/` change, but not for `config.yaml`).

## .env

| Variable | Side | Meaning |
|---|---|---|
| `ANTHROPIC_API_KEY` | server | enables Claude; empty = rule-based fallbacks |
| `VITE_SANAD_API_URL` | browser (public) | API address used by the web UI; default `http://localhost:8010` |
| `SANAD_API_PORT` | launcher | port `run.py` starts the API on; default `8010` |
| `SANAD_WEB_ORIGINS` | server | browser origins allowed to call the API (comma-separated) |
| `SANAD_LOG_FILE` | server | log file path; `none` = console only; empty = `config.yaml` value |
| `SIGN_DATASET_DIR` | server | dataset location if not in `src/data/dataset` |
| `SANAD_SPEECH_PRELOAD` | launcher | `1` (default in `run.py`) loads Whisper when the API starts; `0` = on the first microphone question |

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
