# SANAD · سَند

An AI agent that helps deaf and hard-of-hearing job seekers in Saudi Arabia:

- **Job matching**: reads the candidate's CV and recommends suitable jobs with a match % and a reason.
- **Interview translation**: the recruiter's speech becomes text; the candidate's Saudi Sign Language
  becomes Arabic sentences they approve before sending.
- **Human interpreter**: one button (or too many "None of these") brings a human sign-language interpreter in.

## Quick start

Needs Python 3.10+ and, for the web UI, Node.js 22.12+.

```bash
python run.py setup    # first time: .venv, Python + web packages, .env
python run.py          # agents API + web UI
```

| Open | URL |
|---|---|
| Web UI | <http://localhost:3000> |
| API docs | <http://localhost:8010/docs> |
| Logs | `src/logger/logs/sanad.log` |

Other commands: `python run.py test` · `python run.py api` · `python run.py web`.
Claude is optional: add `ANTHROPIC_API_KEY` to `.env`; without it the agents use simple rules.

## Documentation

| | |
|---|---|
| [Getting started](docs/getting-started.md) | install, run, test, troubleshooting |
| [Architecture](docs/architecture.md) | how the parts fit together |
| [Agents](docs/agents.md) | Job Agent and Interview Agent, their tools and fallbacks |
| [API reference](docs/api.md) | `POST /jobs/recommend`, `WS /interview/{session}` |
| [Database](docs/database.md) | tables and the `instance/` folder |
| [Logging](docs/logging.md) | reading the logs, tags, request ids |
| [Sign recognition](docs/sign-recognition.md) | sign gallery and keypoint format |
| [Speech-to-text](docs/speech.md) | Whisper Large-v3, Arabic only, from the interview microphone |
| [Configuration](docs/configuration.md) | `config.yaml` and `.env` |

## Project structure

```
SANAD/
├── run.py            One command to set up, run and test
├── src/
│   ├── web/          Web UI (TanStack Start + React)
│   ├── agent/        Agents (Python + LangGraph + Claude)
│   │   ├── api.py            FastAPI app
│   │   ├── schemas.py        enums · Claude response models · WebSocket messages
│   │   ├── core/             config loading
│   │   ├── inference/        Claude client · sign matching · speech fallback · gallery builder
│   │   ├── job_agent/        read_cv · search_jobs · score_job
│   │   ├── interview_agent/  speech_to_text · recognize_sign · compose_sentence · call_interpreter
│   │   └── tests/            Python tests
│   ├── database/     schema.sql · db.py (SQLite)
│   ├── logger/       shared logger · logs/sanad.log (not in git)
│   └── data/         jobs.json · sign_gallery/ · sample_cvs/ · dataset/ (Saudi Sign Language)
├── instance/         Runtime data: sanad.db (not in git)
├── docs/             Documentation
├── config/           Tool configs (vite · vitest · eslint · prettier)
├── public/           Logo and favicon
├── config.yaml       Sanad settings
├── requirements.txt  Python dependencies
└── .env.example      Secrets and local settings (copy to .env)
```

## Status

| Part | State |
|---|---|
| Web UI | done (demo data; not connected to the API yet) |
| Job Agent + API | done, tested |
| Interview Agent + API | done, tested |
| Sign recognition | code done; gallery not built yet (see [Sign recognition](docs/sign-recognition.md)) |
