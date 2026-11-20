"""Small text helpers shared by the Job Agent tools."""
from __future__ import annotations

import re

_ARABIC_DIACRITICS = re.compile(r"[ً-ْـ]")

# Arabic <-> English city names, so "الرياض" and "Riyadh" match.
CITY_ALIASES = {
    "riyadh": ["riyadh", "الرياض"],
    "jeddah": ["jeddah", "jidda", "جدة", "جده"],
    "dammam": ["dammam", "الدمام"],
    "khobar": ["khobar", "al khobar", "الخبر"],
    "makkah": ["makkah", "mecca", "مكة", "مكه"],
    "madinah": ["madinah", "medina", "المدينة", "المدينه"],
    "abha": ["abha", "أبها", "ابها"],
    "tabuk": ["tabuk", "تبوك"],
    "remote": ["remote", "عن بعد", "عن بُعد"],
}
# Cities close enough to count when the search is widened.
NEARBY_CITIES = {
    "riyadh": {"riyadh"},
    "jeddah": {"jeddah", "makkah"},
    "makkah": {"makkah", "jeddah"},
    "dammam": {"dammam", "khobar"},
    "khobar": {"khobar", "dammam"},
}


def normalize(text: str) -> str:
    """Lower-case, strip Arabic diacritics/tatweel and unify alef/ya/ta-marbuta."""
    text = _ARABIC_DIACRITICS.sub("", text or "").lower().strip()
    return text.translate(str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي", "ة": "ه"}))


def canonical_city(city: str | None) -> str | None:
    if not city:
        return None
    norm = normalize(city)
    for key, aliases in CITY_ALIASES.items():
        if any(normalize(a) in norm for a in aliases):
            return key
    return norm


# Arabic <-> English skill names used in the web UI and jobs.json.
SKILL_ALIASES = {
    "data analysis": ["data analysis", "تحليل البيانات", "تحليل بيانات"],
    "written communication": ["written communication", "التواصل الكتابي", "تواصل كتابي"],
    "problem solving": ["problem solving", "حل المشكلات", "حل المشاكل"],
    "user research": ["user research", "بحث المستخدم", "بحث المستخدمين"],
    "design": ["design", "التصميم", "تصميم"],
    "excel": ["excel", "اكسل", "إكسل"],
    "sql": ["sql"],
    "crm": ["crm"],
    "figma": ["figma", "فيجما"],
}


def canonical_skill(skill: str) -> str:
    norm = normalize(skill)
    for key, aliases in SKILL_ALIASES.items():
        if norm in {normalize(a) for a in aliases}:
            return key
    return norm


def known_skill_terms(extra: list[str] | None = None) -> dict[str, str]:
    """{surface form (normalized): canonical skill} for keyword search in a CV."""
    terms = {normalize(a): key for key, aliases in SKILL_ALIASES.items() for a in aliases}
    for skill in extra or []:
        terms.setdefault(normalize(skill), canonical_skill(skill))
    return terms
