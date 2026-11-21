"""Projects and certificates, read the way an ATS stores them."""
from __future__ import annotations

import re

from src.agent.text.arabic import ar_digits, normalize_arabic, unique_strings

from .experience import BULLET, _title_case_ratio
from .skills import clean_item, find_skills, split_list

_SENTENCE_END = re.compile(r"[.!?؟]$")
_SMALL = {"of", "and", "the", "for", "in", "at", "on", "to", "with", "a", "an", "by", "from", "using"}


def _is_project_header(line: str) -> bool:
    """«AI Therapeutic App (Rakeez), OpenAI API(GPT-4), Python, Flutter» -> a project header (name + tools)."""
    if BULLET.search(line) or _SENTENCE_END.search(line) or re.match("[a-z]", line) or len(line) > 170:
        return False
    parts = split_list(line, re.compile("[,،|]"))
    name = parts[0] if parts else line
    if re.search("[ء-ي]", name):
        return len(name.split()) <= 10
    return _title_case_ratio(name, _SMALL) >= 0.5 and len(name.split()) <= 14


def tool_skills(tools: list[str]) -> list[str]:
    """Tools as skills: known ones by their skill name, others as written when they look like a tool name."""
    out = []
    for tool in tools:
        known = find_skills(tool)
        if known:
            out.extend(known)
            continue
        value = clean_item(tool)
        if value and len(value.split()) <= 3 and re.match("[A-Zء-ي]", value):
            out.append(value)
    return unique_strings(out)


def parse_projects(lines: list[str]) -> list[dict]:
    projects: list[dict] = []
    current: dict | None = None
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        if _is_project_header(line):
            parts = [p.strip() for p in split_list(line, re.compile("[,،]")) if p.strip()]
            if len(parts) == 1 and " | " in line:
                parts = re.split(r"\s+\|\s+", line)
            current = {"name": clean_item(parts[0] if parts else line), "tools": [t for t in (clean_item(p) for p in parts[1:]) if t], "description": ""}
            projects.append(current)
            continue
        if not current:
            continue
        text = BULLET.sub("", line, count=1)
        current["description"] = f"{current['description']} {text}" if current["description"] else text
    out = []
    for project in [p for p in projects if len(p["name"]) >= 3][:8]:
        description = project["description"]
        if len(description) > 220:
            description = f"{re.sub(r'\s\S*$', '', description[:217])}…"
        out.append({**project, "description": description})
    return out


def parse_certifications(lines: list[str]) -> list[dict]:
    """«• Azure AI Fundamentals (AI-900) – Microsoft • SQL Server – Tuwaiq Academy» -> two certificates."""
    out = []
    for line in lines:
        for piece in re.split(r"\s*[•▪●]\s*|\s+\|\s+", line):
            item = BULLET.sub("", piece, count=1).strip()
            if len(item) < 4:
                continue
            found = re.search(r"(?:19|20)\d{2}", item)
            year = found.group(0) if found else None
            text = re.sub(r"\s+", " ", re.sub(r"[(\[]?\s*(?:19|20)\d{2}\s*[)\]]?", " ", item))
            text = re.sub(r"[\s,،\-–—]+$", "", text).strip()
            parts = re.split(r"\s+[–—-]\s+", text)
            last = parts[-1]
            has_issuer = len(parts) >= 2 and len(last.split()) <= 5
            name = " – ".join(parts[:-1]) if has_issuer else text
            if len(name) < 3:
                continue
            out.append({"name": name, "issuer": last if has_issuer else "", "year": year})
    seen: set[str] = set()
    unique = []
    for item in out:
        key = normalize_arabic(item["name"])
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique[:12]


def format_certification(item: dict) -> str:
    return " · ".join(p for p in [item["name"], item["issuer"], ar_digits(item["year"]) if item.get("year") else ""] if p)
