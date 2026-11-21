"""Tool: read_cv — extracts skills, major, experience and city from the CV.

Supports .pdf, .txt/.md and .json (already-structured profile).
Reads the CV like an ATS (teammate's reader, ported): roles by kind, education, projects, skills and an ATS score;
Claude's reading is added and verified against the text when a key is set. Never logs CV contents.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from src.agent.job_agent.ats.reader import read_profile
from src.agent.schemas import MissingField
from src.logger import get_logger, log_step

from ._text import CITY_ALIASES, canonical_city, known_skill_terms, normalize
from .search_jobs import load_jobs

log = get_logger("job_agent.read_cv")


class ReadCvInput(BaseModel):
    """Parameters of read_cv."""
    cv_file: str = Field(description="Path of the uploaded CV file: .pdf, .docx, .txt, .md or .json")


def cv_text(cv_file: str) -> str:
    path = Path(cv_file)
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        from pypdf import PdfReader

        return "\n".join(page.extract_text() or "" for page in PdfReader(path).pages)
    if suffix == ".docx":   # a .docx is a zip; the text is in word/document.xml (<w:t> runs, <w:p> paragraphs)
        import zipfile
        from xml.etree import ElementTree

        ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
        with zipfile.ZipFile(path) as docx:
            root = ElementTree.fromstring(docx.read("word/document.xml"))
        return "\n".join("".join(t.text or "" for t in p.iter(f"{ns}t")) for p in root.iter(f"{ns}p"))
    if suffix == ".doc":   # legacy Word: text is stored as UTF-16LE runs; keep runs of readable characters
        import unicodedata

        decoded = path.read_bytes().decode("utf-16-le", errors="ignore")
        runs, current = [], []
        for char in decoded:
            if char.isalnum() or char.isspace() or unicodedata.category(char).startswith("P"):
                current.append(char)
                continue
            if len(current) >= 4:
                runs.append("".join(current))
            current = []
        if len(current) >= 4:
            runs.append("".join(current))
        return "\n".join(run for run in runs if re.search(r"[^\W\d_]{3,}", run))
    return path.read_text(encoding="utf-8", errors="ignore")


def _empty_profile() -> dict:
    return {"skills": [], "major": None, "experience_years": None, "city": None}


def _clean(profile: dict) -> dict:
    out = _empty_profile()
    skills = profile.get("skills") or []
    out["skills"] = list(dict.fromkeys(str(s).strip() for s in skills if str(s).strip()))
    out["major"] = (str(profile["major"]).strip() or None) if profile.get("major") else None
    years = profile.get("experience_years")
    try:
        out["experience_years"] = float(years) if years is not None else None
    except (TypeError, ValueError):
        out["experience_years"] = None
    out["city"] = (str(profile["city"]).strip() or None) if profile.get("city") else None
    return out


def _rules(text: str) -> dict:
    norm = normalize(text)
    job_skills = [s for job in load_jobs() for s in job.get("skills", [])]
    skills = [canon for term, canon in known_skill_terms(job_skills).items()
              if re.search(rf"(?<!\w)(?:[وبلف])?{re.escape(term)}(?!\w)", norm)]  # و/ب/ل/ف prefixes
    city = next((key for key, aliases in CITY_ALIASES.items() if key != "remote"
                 and any(normalize(a) in norm for a in aliases)), None)
    years = None
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:\+\s*)?(?:years?|yrs?|سنوات|سنة|سنين)", norm)
    if m:
        years = float(m.group(1))
    elif "سنتان" in norm or "سنتين" in norm:
        years = 2.0
    major = None
    m = re.search(r"(?:major|degree|bachelor(?:'s)? (?:of|in)|بكالوريوس|تخصص)\s*[:\-]?\s*([^\n,.;]{3,60})", text, re.I)
    if m:
        major = m.group(1).strip()
    return {"skills": list(dict.fromkeys(skills)), "major": major, "experience_years": years, "city": city}


def _summary(p: dict) -> str:
    return (f"skills={len(p['skills'])} major={'yes' if p['major'] else 'no'} "
            f"years={p['experience_years']} city={canonical_city(p['city']) or 'none'}")


@log_step(summary=_summary)
def read_cv(cv_file: str) -> dict:
    """Return {"skills": [...], "major": ..., "experience_years": ..., "city": ...}."""
    suffix = Path(cv_file).suffix.lower()
    if suffix == ".json":
        log.info("[INPUT] structured profile (.json)")
        return _clean(json.loads(Path(cv_file).read_text(encoding="utf-8")))
    text = cv_text(cv_file)
    log.info("[INPUT] %s file, %d characters of text", suffix, len(text))
    if not text.strip():
        log.warning("[WARN] CV has no readable text (scanned PDF?) -> empty profile")
        return _empty_profile()
    # The ATS reader (offline, plus Claude verified against the text when a key is set) gives the full profile:
    # roles by kind, education, projects, skills and the ATS report. The short fields below stay for the agent's
    # own decisions (missing city / skills) and for the catalogue search.
    ats, reading = read_profile(text, Path(cv_file).name)
    profile = _clean(_rules(text))
    if profile["experience_years"] is None and ats.get("yearsExperience") is not None:
        profile["experience_years"] = float(ats["yearsExperience"])
    if not profile["city"]:
        profile["city"] = canonical_city((ats.get("ats") or {}).get("contact", {}).get("city"))
    if not profile["major"] and ats.get("education"):
        profile["major"] = ats["education"][0].split(" · ")[0]
    profile["ats_profile"] = ats
    profile["reading"] = {name: {"status": status, "detail": detail} for name, (status, detail) in reading.items()}
    return profile


def missing_fields(profile: dict) -> list[MissingField]:
    """Fields the agent must ask about before searching (skills and city)."""
    missing = []
    if not profile.get("skills"):
        missing.append(MissingField.SKILLS)
    if not canonical_city(profile.get("city")):
        missing.append(MissingField.CITY)
    return missing


read_cv_tool = StructuredTool.from_function(
    read_cv, name="read_cv", args_schema=ReadCvInput,
    description="Read a candidate's CV and return skills, major, years of experience and city.")
