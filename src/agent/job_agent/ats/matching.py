"""Job matching, ATS-style: the percentage is a real, explainable comparison (no base score).

    requirements / keywords  55%   every skill the job asks for, looked up in the candidate's skills, the broader
                                   skills their tools prove, and the full CV text under all its spellings
    related experience       20%   titles actually held, then roles the CV suits — only with real skill overlap
    experience level         10%   years vs. the years the posting asks for
    degree                    5%
    location / work mode     10%
The reason lists the matched requirements and the gaps (in Arabic).
"""
from __future__ import annotations

import re
from functools import lru_cache

from src.agent.text.arabic import ar_digits, js_round, normalize_arabic, tokenize

from .skills import canonical_skill, display_skill, find_skills, mentions_skill, skill_group, with_implied_skills

_STOP = {normalize_arabic(w) for w in ["في", "من", "إلى", "على", "عن", "مع", "and", "of", "the", "for", "a", "an", "و", "أو", "specialist", "أخصائي",
                                        "اخصائية", "trainee", "intern", "co-op", "junior", "senior", "lead", "متدرب", "متدربة", "مبتدئ", "أول", "digital",
                                        "رقمي", "services", "service", "quality", "officer", "موظف", "assistant", "مساعد", "core", "member", "عضو"]}
# Role words in both languages, so «أخصائي موارد بشرية» meets «Head of Human Resources» and «HR Specialist».
_ROLE_WORDS = {
    "hr": ["human", "resources"], "ai": ["artificial", "intelligence"], "ml": ["machine", "learning"], "bi": ["business", "intelligence"],
    "it": ["information", "technology"], "ui": ["interface"], "ux": ["experience"], "qa": ["quality"],
    "موارد": ["human", "resources", "hr"], "بشريه": ["human"], "توظيف": ["recruitment", "talent"], "محاسب": ["accountant", "accounting"],
    "محاسبه": ["accountant", "accounting"], "مالي": ["finance", "financial"], "مهندس": ["engineer"], "هندسه": ["engineering", "engineer"],
    "ميكانيكي": ["mechanical"], "كهربائي": ["electrical"], "مدني": ["civil"], "محلل": ["analyst"], "بيانات": ["data"], "مطور": ["developer", "engineer"],
    "برمجيات": ["software"], "مصمم": ["designer"], "ممرض": ["nurse", "nursing"], "ممرضه": ["nurse", "nursing"], "تسويق": ["marketing"], "مبيعات": ["sales"],
    "امن": ["security"], "سيبراني": ["cybersecurity", "cyber"], "ذكاء": ["ai", "artificial", "intelligence"], "اصطناعي": ["ai", "artificial"],
    "اداري": ["administrative", "admin"], "معلم": ["teacher"], "مدرب": ["trainer"], "صيدلي": ["pharmacist"], "فني": ["technician"], "عملاء": ["customer"],
    "مشتريات": ["procurement"], "مشاريع": ["project"], "جوده": ["quality"],
}


def title_tokens(value: str) -> list[str]:
    return list(_title_tokens(value))


@lru_cache(maxsize=16384)
def _title_tokens(value: str) -> tuple[str, ...]:
    tokens = [t for t in tokenize(value) if (len(t) > 2 or t in _ROLE_WORDS) and t not in _STOP]
    return tuple(t for t in dict.fromkeys([*tokens, *(w for t in tokens for w in _ROLE_WORDS.get(t, []))]) if len(t) > 1)


def _list_ar(items: list[str]) -> str:
    return "".join(items) if len(items) <= 1 else f"{'، '.join(items[:-1])} و{items[-1]}"


@lru_cache(maxsize=65536)
def skills_match(a: str, b: str) -> bool:
    """Same skill? Canonical names first, then containment / shared words for skills outside the taxonomy."""
    left, right = normalize_arabic(canonical_skill(a)), normalize_arabic(canonical_skill(b))
    if left == right:
        return True
    if min(len(left), len(right)) >= 4 and (left in right or right in left):
        return True
    left_words = {w for w in tokenize(left) if len(w) > 2 and w not in _STOP}
    right_words = [w for w in tokenize(right) if len(w) > 2 and w not in _STOP]
    if not left_words or not right_words:
        return False
    shared = sum(1 for w in right_words if w in left_words)
    return shared / len(left_words | set(right_words)) >= 0.5


def match_job(profile: dict, job: dict, cv_text: str = "") -> dict:
    """{score, reason, matchedSkills, missingSkills}. `job` has title, english, description, skills, location, mode."""
    normalized_cv = normalize_arabic(cv_text) if cv_text else ""
    own = [*profile.get("skills", []), *profile.get("languages", [])]
    candidate = with_implied_skills(own)

    def strict(skill: str) -> bool:
        """A named tool («AutoCAD», «Salesforce») needs that tool; a skill («CRM», «تحليل البيانات», «Data analysis») accepts
        any spelling and its tools. A concept written in English is shown by its Arabic name, a tool keeps its own."""
        if re.search("[ء-ي]", skill) or normalize_arabic(canonical_skill(skill)) == normalize_arabic(skill):
            return False
        return display_skill(skill) == skill.strip()

    requirements: dict[str, str] = {}
    for skill in [*job.get("skills", []), *find_skills(job.get("description", ""))]:
        key = normalize_arabic(skill) if strict(skill) else normalize_arabic(canonical_skill(skill))
        if skill.strip() and key not in requirements:
            requirements[key] = skill.strip()
    job_skills = list(requirements.values())

    def has(skill: str) -> bool:
        found = (any(normalize_arabic(i) == normalize_arabic(skill) for i in own) if strict(skill)
                 else any(skills_match(i, skill) for i in candidate))
        return found or (normalized_cv != "" and mentions_skill(normalized_cv, skill))

    matched = [s for s in job_skills if has(s)]
    missing = [s for s in job_skills if s not in matched]

    def weight(skill: str) -> float:
        return 0.5 if (skill_group(skill) or "") in ("soft", "language") else 1

    total_weight = sum(weight(s) for s in job_skills)
    keyword_score = min(1, sum(weight(s) for s in matched) / min(total_weight, 6)) if job_skills else 0
    hard_matched = [s for s in matched if weight(s) == 1]

    role_tokens = set(title_tokens(f"{job.get('title', '')} {job.get('english', '')}"))

    def shares_token(title: str) -> bool:
        return any(t in role_tokens for t in title_tokens(title))

    held = next((t for t in profile.get("jobTitles", []) if shares_token(t)), None)
    suited = None if held else next((t for t in [*profile.get("suggestedRoles", []), *profile.get("searchKeywords", [])] if shares_token(t)), None)
    title_score = 1 if held else 0.6 if suited else 0

    description = normalize_arabic(job.get("description", ""))
    required = re.search(r"(\d{1,2})\s*\+?\s*(?:سنوات|سنة|سنه|years?|yrs)", description, re.I | re.ASCII)
    years = profile.get("yearsExperience") or 0
    if required:
        experience_score = min(1, years / max(1, int(required.group(1))))
    else:
        experience_score = 1 if years >= 1 else 0.75 if years > 0 else 0.5 if profile.get("experience") else 0.3
    needs_degree = bool(re.search(r"(بكالوريوس|bachelor|degree|شهاده جامعيه|university)", description, re.I))
    education_score = 1 if profile.get("education") else 0.2 if needs_degree else 0.6
    mode = normalize_arabic(job.get("mode") or "")
    city = normalize_arabic(((profile.get("ats") or {}).get("contact") or {}).get("city") or "")
    location = normalize_arabic(job.get("location") or "")
    if re.search("بعد|remote", mode) or re.search("بعد|remote", location):
        location_score = 1
    elif city and location and (city in location or location in city):
        location_score = 1
    else:
        location_score = 0.7 if re.search("هجين|hybrid", mode) else 0.5

    relevance = title_score * (1 if hard_matched else 0.4)   # a similar title alone must not lift the score
    raw = keyword_score * 0.55 + relevance * 0.2 + experience_score * 0.1 + education_score * 0.05 + location_score * 0.1
    score = max(5, min(98, js_round(raw * 100 * (1 if matched else 0.6))))

    gap = f"؛ ينقصك: {_list_ar(missing[:2])}" if missing else ""
    if len(matched) >= 2:
        reason = f"لأن سيرتك تحتوي {ar_digits(len(matched))} من {ar_digits(len(job_skills))} كلمات مفتاحية للدور ({_list_ar(matched[:3])}){gap}."
    elif len(matched) == 1 and held:
        reason = f"لأن خبرتك في {held} ومهارة {matched[0]} قريبة من هذا الدور{gap}."
    elif len(matched) == 1 and suited:
        reason = f"لأن سيرتك تناسب دور {suited}، ومهارة {matched[0]} من متطلباته{gap}."
    elif len(matched) == 1:
        reason = f"لأن مهارة {matched[0]} من متطلبات الدور{gap}."
    elif held:
        reason = f"لأن خبرتك في {held} قريبة من هذا الدور{gap}."
    elif suited:
        reason = f"لأن سيرتك تناسب دور {suited}{gap}."
    else:
        reason = f"توافق أولي؛ يطلب الدور مهارات مثل {_list_ar(missing[:3])}." if missing else "توافق أولي مع مهاراتك الحالية."
    return {"score": score, "reason": reason, "matchedSkills": matched, "missingSkills": missing}
