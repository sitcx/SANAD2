-- Sanad database schema (SQLite for the hackathon).

CREATE TABLE IF NOT EXISTS candidates (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT NOT NULL,
    city         TEXT,
    profile_json TEXT,                -- output of read_cv
    created_at   TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS jobs (
    id          TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    company     TEXT,
    city        TEXT,
    mode        TEXT,                 -- onsite / hybrid / remote
    description TEXT,
    skills_json TEXT
);

CREATE TABLE IF NOT EXISTS interviews (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id        INTEGER REFERENCES candidates(id),
    job_id              TEXT REFERENCES jobs(id),
    mode                TEXT CHECK (mode IN ('human', 'ai')),
    none_count          INTEGER DEFAULT 0,
    interpreter_called  INTEGER DEFAULT 0,   -- 0/1
    interpreter_reason  TEXT,                -- 'button' | 'none_limit'
    created_at          TEXT DEFAULT CURRENT_TIMESTAMP
);
