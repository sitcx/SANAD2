"""ATS-style CV reading and job matching (ported from the teammate's TypeScript agents to Python).

    sections    split a CV into standard sections (Arabic and English headings)
    experience  roles with title / organisation / city / dates / kind, durations in Arabic
    records     projects and certificates
    skills      bilingual taxonomy (src/data/skills_taxonomy.json) and skill extraction
    score       ATS score 0-100 with 15 checks and Arabic tips
    reader      the offline profile (heuristic) + Claude's reading verified against the CV text
    matching    weighted job match: requirements 55%, related experience 20%, level 10%, degree 5%, place 10%
"""
