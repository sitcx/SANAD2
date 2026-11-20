# Getting started

## Requirements

| Tool | Version | Needed for |
|---|---|---|
| Python | 3.10 or newer | the agents API |
| Node.js | 22.12 or newer | the web UI ([nodejs.org](https://nodejs.org)) |
| Git LFS | any | only to download the sign-language videos |

Without Node.js the agents API still runs; only the web UI is skipped.

## First run

```bash
python run.py setup
```

This creates `.venv`, installs the Python packages (`requirements.txt`) and the web packages
(`npm install`), and copies `.env.example` to `.env`.

Optional: put your key in `.env` to let Claude read CVs, score jobs and write sentence options:

```
ANTHROPIC_API_KEY=sk-ant-...
```

Without a key everything still works with simple rules (see [Agents → fallbacks](agents.md#fallbacks)).

## Everyday commands

| Command | What it does |
|---|---|
| `python run.py` | starts the agents API **and** the web UI |
| `python run.py api` | agents API only |
| `python run.py web` | web UI only |
| `python run.py test` | Python tests, then web tests |
| `python run.py help` | lists the commands |

Then open:

- Web UI: <http://localhost:3000>
- API docs (interactive): <http://localhost:8010/docs>
- Log file: `src/logger/logs/sanad.log`

Output lines are prefixed `[api]` or `[web]`. Press **Ctrl+C** to stop both.

## Trying the agents

The web UI and the agents run side by side; the web UI still uses its demo data and does not call
the API yet. Try the agents from the interactive API page:

1. Open <http://localhost:8010/docs>.
2. Open **POST /jobs/recommend** → **Try it out**, choose a CV file (PDF, DOCX or TXT) → **Execute**.
3. The response shows the extracted profile and the recommended jobs with match % and reasons.
   If the CV has no city, it answers `need_info`; send again with `answers` = `{"city": "الرياض"}`.

Each step appears in the log, for example `[OK] read_cv (19 ms) -> skills=2 ...`.

## Running without run.py

```bash
# agents
python -m venv .venv
.venv\Scripts\activate                       # Windows (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
uvicorn src.agent.api:app --reload --port 8010

# web (second terminal)
npm install
npm run dev
```

## Tests

| Suite | Command | Location |
|---|---|---|
| Python | `python -m pytest src/agent/tests` | `src/agent/tests/` |
| Web | `npm test` | `src/web/test/` |

Python tests never call Claude and use a temporary database and sign gallery.
`test_logging.py` fails if a tool or database function is added without logging.

## Troubleshooting

| Problem | Fix |
|---|---|
| `Node.js is not installed` | Install Node 22.12+, then close and reopen VS Code / the terminal. |
| `Port 8010 is used by another program` | Another Sanad run is still open, or pick another port: `set SANAD_API_PORT=8020` (then also `VITE_SANAD_API_URL=http://localhost:8020` for the web). |
| `Python packages are not installed` | Run `python run.py setup`. |
| Arabic shows as `????` in the console | Only a display issue of the terminal; `src/logger/logs/sanad.log` is UTF-8. |
| `.doc` file rejected | Old Word format is not supported. Save as PDF or DOCX. |

Why port 8010 and not 8000? Port 8000 is often used by other software (for example Splunk), and
requests would silently go to the wrong program.
