"""Bilingual skills taxonomy and skill extraction for any CV, in any field.

The taxonomy (196 skills with aliases, group and implied skills) lives in src/data/skills_taxonomy.json.
`name` is how a skill is shown; aliases are matched after Arabic normalisation, so «اكسل»,
«Microsoft Excel» and «Excel» are the same skill.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache

from src.agent.core.config import project_path
from src.agent.text.arabic import normalize_arabic, unique_strings

from .sections import Section, lines_of

TAXONOMY_FILE = "src/data/skills_taxonomy.json"


@lru_cache(maxsize=1)
def taxonomy() -> list[dict]:
    return json.loads(project_path(TAXONOMY_FILE).read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _compiled() -> list[tuple[dict, list[str]]]:
    out = []
    for entry in taxonomy():
        patterns = list(dict.fromkeys(p for p in (normalize_arabic(a) for a in [entry["name"], *entry["aliases"]]) if len(p) >= 2))
        out.append((entry, patterns))
    return out


_BOUNDARY = set(" \t\n\r\f\v,،;:()[]/|-•·.!?؟")
_PREFIXED = re.compile(r"(^|\s)(و|ب|ل|ف|ال|وال|بال)$")


def _contains_phrase(haystack: str, phrase: str) -> bool:
    """Word-boundary match for Arabic and Latin (and tokens like c#, .net, node.js); allows «وExcel»."""
    start = 0
    while True:
        index = haystack.find(phrase, start)
        if index == -1:
            return False
        before = haystack[index - 1] if index > 0 else None
        after = haystack[index + len(phrase)] if index + len(phrase) < len(haystack) else None
        prefixed = bool(_PREFIXED.search(haystack[max(0, index - 3):index]))
        if (before is None or before in _BOUNDARY or prefixed) and (after is None or after in _BOUNDARY):
            return True
        start = index + 1


# «data warehouse» is not warehouse management; «in production» is not manufacturing; «we are hiring» is not recruitment.
_AMBIGUOUS = re.compile(
    r"\b(data|lake|snowflake|bigquery|redshift|cloud|analytics|dwh)\s*/?\s*warehous\w*|\bwarehous\w* (solutions?|architecture|design|model\w*|tables?|layer)\b"
    r"|\b(in|into|to|for) production\b|\bproduction[- ](ready|grade|environments?|systems?|deployments?|models?|code|data|issues|support|use)\b"
    r"|\b(we are|we re|now|currently) hiring\b|\bhiring (managers?|teams?|process)\b", re.ASCII)


def _clean(normalized: str) -> str:
    return _AMBIGUOUS.sub(" ", normalized)


def find_skills(text: str) -> list[str]:
    """Taxonomy skills mentioned in free text (CV, job description), ordered by first mention."""
    return list(_find_skills(text))


@lru_cache(maxsize=8192)
def _find_skills(text: str) -> tuple[str, ...]:
    haystack = f" {_clean(normalize_arabic(text))} "
    found = []
    for entry, patterns in _compiled():
        first = None
        for pattern in patterns:
            if len(pattern) <= 2 and not re.search("[a-z]", pattern):
                continue
            if _contains_phrase(haystack, pattern):
                at = haystack.find(pattern)
                first = at if first is None else min(first, at)
        if first is not None:
            found.append((first, entry["name"]))
    return tuple(name for _, name in sorted(found, key=lambda item: item[0]))


@lru_cache(maxsize=65536)
def mentions_skill(normalized_text: str, skill: str) -> bool:
    """Does the (normalised) text mention this skill under any spelling? This is how an ATS scans a CV."""
    key = normalize_arabic(skill)
    entry = next((patterns for item, patterns in _compiled() if normalize_arabic(item["name"]) == key), None)
    patterns = entry if entry else [key]
    haystack = f" {_clean(normalized_text)} "
    return any((len(p) > 2 or re.search("[a-z]", p)) and _contains_phrase(haystack, p) for p in patterns)


@lru_cache(maxsize=16384)
def canonical_skill(skill: str) -> str:
    """Any spelling of a skill -> its canonical name; unknown skills come back trimmed."""
    key = normalize_arabic(skill)
    for entry, patterns in _compiled():
        if key in patterns:
            return entry["name"]
    return skill.strip()


def with_implied_skills(skills: list[str]) -> list[str]:
    """Adds the broader skills that tools prove (Flutter -> mobile development); used for matching."""
    out = list(dict.fromkeys(canonical_skill(s) for s in skills))
    queue = list(out)
    by_name = {entry["name"]: entry for entry in taxonomy()}
    while queue:
        entry = by_name.get(queue.pop())
        for implied in (entry or {}).get("implies", []):
            if implied not in out:
                out.append(implied)
                queue.append(implied)
    return out


@lru_cache(maxsize=16384)
def skill_group(skill: str) -> str | None:
    canonical = canonical_skill(skill)
    return next((entry["group"] for entry in taxonomy() if entry["name"] == canonical), None)


# ---------------------------------------------------------------- extraction from a CV

_LEVEL = re.compile(r"\s*[(\[]?\s*(ممتاز|جيد جدا|جيد جدًا|جيد|متوسط|مبتدئ|متقدم|محترف|خبير|اللغة الأم|اللغه الام|لغة أم|advanced|intermediate|beginner"
                    r"|expert|fluent|native|basic|proficient|good|very good|excellent|\d{1,3}\s*%|[★☆●○]+)\s*[)\]]?\s*$", re.I | re.ASCII)
_NOT_A_SKILL = re.compile(r"(سنوات|سنة|خبرة في|years?|experience|@|https?:|www\.|\d{3,})", re.I | re.ASCII)
_ARABIC = re.compile("[ء-ي]")
# «Data & Analysis:», «Cybersecurity:», «المهارات التقنية:»: category labels inside a skills list.
_LABEL = re.compile(r"(^|[|•;؛]|\s)([A-Za-z][A-Za-z&/ ]{1,28}|[ء-ي][ء-ي ]{1,28})\s*[:：]\s*")
_SEPARATORS = re.compile(r"[,،;؛|•·]|\s{2,}|\s[-–—]\s|\s/\s")
_LIST_SPLIT = re.compile(r"\s{2,}|\s[-–—]\s|\s/\s")


def clean_item(item: str) -> str:
    value = re.sub(r"\s+", " ", re.sub(r"^[•·▪●◦○■□➢➤✓✔*\-–—\d.)\s]+", "", item)).strip()
    for _ in range(2):
        value = _LEVEL.sub("", value).strip()
    value = re.sub(r"[.:؛;]+$", "", value).strip()
    if value.startswith("(") and ")" not in value:
        value = value[1:].strip()
    if value.endswith(")") and "(" not in value:
        value = value[:-1].strip()
    return value


def split_list(text: str, pattern: re.Pattern | None = None) -> list[str]:
    """Splits a comma list, ignoring commas inside brackets: «Elm AI Models (TTS, ASR), Figma»."""
    pattern = pattern or _SEPARATORS
    out, depth, piece = [], 0, ""
    for char in text:
        if char in "([":
            depth += 1
        if char in ")]" and depth > 0:
            depth -= 1
        if depth == 0 and pattern.search(char):
            out.append(piece)
            piece = ""
            continue
        piece += char
    out.append(piece)
    return [part.strip() for chunk in out for part in _LIST_SPLIT.split(chunk) if part.strip()]


def _expand_brackets(item: str) -> list[str]:
    """«UI Design (Figma)» -> «UI Design» + «Figma»; «Web Development (Front End)» stays one skill."""
    match = re.match(r"^(.+?)\s*\((.+)\)$", item)
    if not match:
        return [item]
    inner = [part.strip() for part in re.split("[,،]", match.group(2)) if part.strip()]
    known = [part for part in inner if find_skills(part) or canonical_skill(part) != part]
    if not known:
        return [item]
    outer = canonical_skill(match.group(1).strip())
    return [match.group(1).strip(), *[part for part in known if canonical_skill(part) != outer]]


def _segment(item: str) -> list[str]:
    """Long runs without separators («Organizational Skills Communication Skills») -> known skills."""
    if len(item.split()) <= 5:
        return [item]
    named = [m.group(1) for m in re.finditer(r"([A-Z][A-Za-z-]+(?:\s[A-Z][A-Za-z-]+)?\sSkills)", item) if not find_skills(m.group(1))]
    return [*find_skills(item), *named]


def section_skills(sections: list[Section]) -> list[str]:
    def label(match: re.Match) -> str:
        before = match.group(1)
        return f"{'' if before == ' ' else before} | "

    text = _LABEL.sub(label, " | ".join(lines_of(sections, "skills")))
    items = split_list(text, re.compile(r"[,،;؛|•·]"))
    items = [part for item in items for part in (re.split("[,،]", item.strip()[1:-1]) if re.fullmatch(r"\(.*\)", item.strip()) else [item])]
    items = [clean_item(part) for item in items for part in _segment(item)]
    items = [clean_item(part) for item in items for part in _expand_brackets(item)]
    items = [i for i in items if 1 <= len(i) <= 48 and len(i.split(" ")) <= 6 and not _NOT_A_SKILL.search(i) and re.search("[A-Za-zء-ي]", i)]
    return unique_strings(display_skill(i) for i in items)


# Products and brands keep their own name even when they belong to a broader skill (AutoCAD -> 3D design).
_BRANDS = {"autocad", "revit", "blender", "3ds max", "solidworks", "catia", "canva", "premiere", "after effects", "final cut", "splunk", "qradar",
           "nessus", "burp suite", "docker", "kubernetes", "jenkins", "terraform", "ansible", "jira", "trello", "sap", "oracle", "salesforce",
           "zendesk", "hubspot", "freshdesk", "odoo", "quickbooks", "sage", "primavera", "ms project", "etap", "arcgis", "qgis", "photoshop",
           "illustrator", "indesign", "lightroom", "sketch", "invision", "zeplin", "looker", "qlik", "spss", "sas", "stata", "hadoop", "spark",
           "pyspark", "kafka", "airflow", "opencv", "yolo", "keras", "pandas", "numpy", "dart", "swiftui", "firestore", "xgboost", "raspberry pi",
           "chatgpt", "gpt-4", "ccna", "pmp", "capm", "cissp", "itil", "ifrs", "lean", "six sigma"}


@lru_cache(maxsize=16384)
def display_skill(item: str) -> str:
    """The candidate's own wording for tools («Zendesk»), the shared Arabic name for concepts («Problem solving» -> «حل المشكلات»)."""
    value = item.strip()
    canonical = canonical_skill(value)
    if canonical != value and _ARABIC.search(canonical) and not _ARABIC.search(value):
        if normalize_arabic(value) in _BRANDS or (re.fullmatch(r"[A-Z]{2,6}", value) and value not in canonical):
            return value
        return canonical
    if canonical != value:
        return canonical if (_ARABIC.search(value) or _ARABIC.search(canonical)) else value
    found = find_skills(value)
    if len(found) == 1 and _ARABIC.search(found[0]) and len(value.split()) <= 4 and value not in found:
        return found[0]
    return value


_NOISE = [
    re.compile(r"\bleadership (meetings?|teams?|departments?|members?)\b", re.I | re.ASCII),
    re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+", re.ASCII),
    re.compile(r"https?://\S+|www\.\S+|linkedin\.com/\S+", re.I),
    re.compile(r"\+?\d[\d\s-]{7,}\d", re.ASCII),
]


def without_noise(text: str) -> str:
    for pattern in _NOISE:
        text = pattern.sub(" ", text)
    return text


def extract_skills(sections: list[Section], text: str, *, project_tools: list[str] | None = None,
                   certification_text: str = "", mined_text: str | None = None) -> list[str]:
    listed = section_skills(sections)
    certified = find_skills(certification_text)
    if mined_text is None:
        mined_text = "\n".join(line for s in sections if s.kind not in {"education", "contact", "languages", "header", "awards"} for line in s.lines)
    mined = find_skills(without_noise(mined_text or text))
    seen: set[str] = set()
    covered = {normalize_arabic(s) for s in find_skills("\n".join(listed))}
    ordered: list[str] = []

    def add(skill: str) -> None:
        key = normalize_arabic(skill)
        if not skill or key in seen or skill_group(skill) == "language":
            return
        seen.add(key)
        ordered.append(skill)

    for skill in listed:
        add(skill)
    for skill in [*(project_tools or []), *certified, *mined]:
        if normalize_arabic(canonical_skill(skill)) not in covered:
            add(skill)
    hard = [s for s in ordered if skill_group(s) != "soft"][:22]
    soft = [s for s in ordered if skill_group(s) == "soft"][:8]
    return hard + soft


# (pattern anywhere in the CV, looser pattern inside a languages section, display name)
_LANGUAGES = [
    (r"(لغه الاشاره|sign language)", r"(اشاره|sign|ssl|asl)", "لغة الإشارة السعودية"),
    (r"(اللغه العربيه|\barabic\b)", r"(عربي|arabic)", "العربية"),
    (r"(اللغه الانجليزيه|الانجليزيه|\benglish\b|ielts|toefl)", r"(انجليزي|انكليزي|english)", "الإنجليزية"),
    (r"(اللغه الفرنسيه|\bfrench\b)", r"(فرنسي|french)", "الفرنسية"),
    (r"(اللغه الارديه|\burdu\b)", r"(اردي|اوردو|urdu)", "الأردية"),
    (r"(اللغه الهنديه|\bhindi\b)", r"(هندي|hindi)", "الهندية"),
    (r"(اللغه الاسبانيه|\bspanish\b)", r"(اسباني|spanish)", "الإسبانية"),
    (r"(اللغه الالمانيه|\bgerman\b)", r"(الماني|german)", "الألمانية"),
    (r"(اللغه التركيه|\bturkish\b)", r"(تركي|turkish)", "التركية"),
    (r"(اللغه الصينيه|\bchinese\b|mandarin)", r"(صيني|chinese|mandarin)", "الصينية"),
]


def extract_languages(sections: list[Section], text: str) -> list[str]:
    in_section = normalize_arabic(" ".join(lines_of(sections, "languages")))
    whole = normalize_arabic(text)
    return unique_strings(name for anywhere, loose, name in _LANGUAGES
                          if re.search(loose, in_section, re.ASCII) or re.search(anywhere, whole, re.ASCII))
