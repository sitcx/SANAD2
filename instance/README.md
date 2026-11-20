# instance/

Runtime data that belongs to this machine only. Everything here except this file is ignored by git.

| File | Created by | Content |
|---|---|---|
| `sanad.db` | the API on startup (`db.init_db()`) | SQLite database: candidates, jobs, interviews |

- Safe to delete: the database is recreated (empty, with jobs from `src/data/jobs.json`) on the next start.
- The location is set in `config.yaml` → `database.path`.
- Never commit it: it holds candidate profiles.

See [docs/database.md](../docs/database.md).
