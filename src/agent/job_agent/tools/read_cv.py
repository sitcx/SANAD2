"""Tool: read_cv — extracts skills, major, experience and city from the CV.

Supports .pdf, .txt/.md and .json (already-structured profile).
Uses Claude when available; otherwise keyword rules. Never logs CV contents.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from src.agent.inference.llm import ask_claude, llm_available
from src.agent.schemas import CvProfileResponse, MissingField
from src.logger import get_logger, log_step

from ._text import CITY_ALIASES, canonical_city, known_skill_terms, normalize
from .search_jobs import load_jobs

log = get_logger("job_agent.read_cv")


class ReadCvInput(BaseModel):
    """Parameters of read_cv."""
    cv_file: str = Field(description="Path of the uploaded CV file: .pdf, .docx, .txt, .md or .json")


_PROMPT = """Extract the candidate profile from this CV (Arabic or English).
Leave a field empty when the CV does not say. Do not invent information.

CV:
<<<
{cv}
>>>"""


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
    if llm_available():
        try:
            reply = ask_claude(_PROMPT.format(cv=text[:12000]), CvProfileResponse)
            log.info("[LLM] profile extracted by Claude (validated)")
            return _clean(reply.model_dump())
        except Exception as exc:  # noqa: BLE001 - fall back to rules (incl. pydantic ValidationError)
            log.warning("[FALLBACK] Claude failed (%s) -> keyword rules", type(exc).__name__)
    else:
        log.info("[FALLBACK] no ANTHROPIC_API_KEY -> keyword rules")
    return _clean(_rules(text))


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
