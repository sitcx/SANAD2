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

-- Company side: job postings, the candidate pool and applications.
CREATE TABLE IF NOT EXISTS postings (
    id          TEXT PRIMARY KEY,
    company     TEXT NOT NULL,
    title       TEXT NOT NULL,
    city        TEXT,
    mode        TEXT,
    salary      TEXT,
    description TEXT,
    skills_json TEXT NOT NULL,
    min_years   INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS talents (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    mode        TEXT NOT NULL CHECK (mode IN ('sign', 'voice')),
    years       INTEGER NOT NULL DEFAULT 0,
    city        TEXT,
    skills_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS applications (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    posting_id    TEXT NOT NULL REFERENCES postings(id) ON DELETE CASCADE,
    talent_id     TEXT NOT NULL REFERENCES talents(id) ON DELETE CASCADE,
    status        TEXT NOT NULL,
    interview_at  TEXT,
    retained      INTEGER,               -- hired only: 1 still employed, 0 left
    updated_at    TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (posting_id, talent_id)
);

-- Job agent (CV reader, matching, job search): one analysed profile per candidate, match per job, agent runs.
CREATE TABLE IF NOT EXISTS cv_profiles (
    candidate_id    TEXT PRIMARY KEY,         -- talent id (company side) or job-agent candidate id
    profile_json    TEXT NOT NULL,            -- ATS profile: skills, roles by kind, education, projects, ATS report
    engine          TEXT NOT NULL,            -- heuristic | claude
    parser_version  INTEGER NOT NULL,
    cv_text         TEXT,                     -- extracted text: re-matching scans it like an ATS; re-read when the reader improves
    updated_at      TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS job_matches (
    candidate_id    TEXT NOT NULL,
    job_id          TEXT NOT NULL,
    score           INTEGER NOT NULL,
    reason          TEXT NOT NULL,
    matched_json    TEXT NOT NULL,
    missing_json    TEXT NOT NULL,
    updated_at      TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (candidate_id, job_id)
);

CREATE TABLE IF NOT EXISTS agent_runs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    agent         TEXT NOT NULL,              -- cv | jobs-personal | jobs-sources
    candidate_id  TEXT,
    status        TEXT NOT NULL,              -- running | succeeded | failed
    stats_json    TEXT NOT NULL DEFAULT '{}', -- stages (name, label, status, detail) or search counts
    error         TEXT,
    started_at    TEXT DEFAULT CURRENT_TIMESTAMP,
    finished_at   TEXT
);
