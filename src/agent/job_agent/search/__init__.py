"""Job search agent (ported from the teammate's TypeScript): finds real, open jobs for one candidate.

    sources    public job APIs that need no AI key (Workable, career boards, Remotive, Jobicy, Himalayas, Remote OK, X)
    feeds      JSON / RSS / Atom job feeds
    discovery  Claude with web search + web fetch, recording each verified posting; cooldowns per candidate
Found jobs are stored in the `postings` table next to the company's jobs (src/database/candidate_db.py).
"""
