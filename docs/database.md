# Database

SQLite, file `instance/sanad.db` (set in `config.yaml` → `database.path`).

- Created automatically when the API starts (`init_db()`), together with the jobs from `src/data/jobs.json`.
- `instance/` is ignored by git: the file holds candidate profiles. Delete it any time to start fresh.
- Tests use a temporary database, never this file.

## Tables — `src/database/schema.sql`

```mermaid
erDiagram
    candidates ||--o{ interviews : has
    jobs ||--o{ interviews : for
    candidates {
        int id PK
        text name
        text city
        text profile_json "output of read_cv"
        text created_at
    }
    jobs {
        text id PK
        text title
        text company
        text city
        text mode "onsite / hybrid / remote"
        text description
        text skills_json
    }
    interviews {
        int id PK
        int candidate_id FK
        text job_id FK
        text mode "human / ai"
        int none_count
        int interpreter_called "0 / 1"
        text interpreter_reason "button / none_limit"
        text created_at
    }
```

## Functions — `src/database/db.py`

| Function | Used by | Does |
|---|---|---|
| `init_db()` | API startup | creates tables, loads `jobs.json` |
| `save_candidate(name, profile)` → id | `POST /jobs/recommend` | stores the candidate and extracted profile |
| `list_jobs()` | — | all jobs with skills as a list |
| `start_interview(candidate_id, job_id, mode)` → id | WebSocket start | creates an interview row |
| `update_interview(id, **fields)` | every WebSocket event | updates `mode`, `none_count`, `interpreter_called`, `interpreter_reason` |
| `get_interview(id)` | tests | one interview row |

Every function logs `[START]` / `[OK]` / `[FAIL]` (logger `database.db`).

## Looking inside

```bash
.venv\Scripts\python -c "import sqlite3; c = sqlite3.connect('instance/sanad.db'); print(c.execute('select * from interviews').fetchall())"
```

Or open the file with any SQLite viewer (for example the *SQLite Viewer* VS Code extension).
