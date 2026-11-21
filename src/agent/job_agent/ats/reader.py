"""The CV profile: offline ATS reading, and Claude's reading verified against the CV text.

heuristic_profile()       no network, deterministic: sections, roles by kind, dates, projects, skills, ATS score
verified_claude_profile() keeps only what the CV supports (every role and skill needs a quote found in the text)
merge_profiles()          Claude first; the offline reader fills what Claude left out and scores the file for ATS
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

from src.agent.text.arabic import js_round, normalize_arabic, tokenize, unique_strings

from .experience import (DEGREE, duration_ar, find_date_range, format_education, format_experience, months_of, parse_education, parse_roles,
                         period_ar, piece_kind, total_years)
from .records import format_certification, parse_certifications, parse_projects, tool_skills
from .score import ats_report
from .sections import cv_lines, lines_of, split_sections
from .skills import canonical_skill, display_skill, extract_languages, extract_skills, find_skills, skill_group, without_noise

PARSER_VERSION = 4
_CERTIFICATE = re.compile(r"(شهاده|دوره|برنامج تدريبي|رخصه|certificate|certification|certified|course|license|bootcamp)", re.I | re.ASCII)
_YEARS_STATED = re.compile(r"(\d{1,2})\+?\s*(?:سنوات|سنه|عام|اعوام|years?|yrs)\s*(?:من\s*)?(?:الخبره|خبره|of experience|experience)", re.I | re.ASCII)
_INTERN_WORDS = re.compile(r"\b(trainee|intern|internship|co-?op|apprentice)\b|متدرب(ة|ه)?|تدريب تعاوني", re.I | re.ASCII)
_GENERIC_SKILLS = {"Excel", "Microsoft Office", "Word", "PowerPoint", "Outlook وTeams", "Google Workspace", "إعداد التقارير", "الطباعة السريعة", "ERP"}
_ROLE_BY_GROUP = {
    "data": "محلل بيانات", "ai": "أخصائي ذكاء اصطناعي", "security": "أخصائي أمن سيبراني", "software": "مطور برمجيات", "design": "مصمم جرافيك وتجربة مستخدم",
    "admin": "موظف إداري ومدخل بيانات", "service": "أخصائي تسويق رقمي وخدمة عملاء", "finance": "محاسب", "hr": "أخصائي موارد بشرية",
    "operations": "أخصائي عمليات ومستودعات", "health": "أخصائي رعاية صحية", "education": "مدرب ومعلم", "engineering": "مهندس",
    "legal": "أخصائي قانوني وامتثال", "media": "صانع ومحرر محتوى", "hospitality": "موظف ضيافة", "crafts": "فني صيانة وحرف",
}
_ROLE_EN = {
    "data": "Data Analyst", "ai": "AI Engineer", "security": "Cybersecurity Analyst", "software": "Software Developer", "design": "UI/UX Designer",
    "admin": "Administrative Assistant", "service": "Customer Service Specialist", "finance": "Accountant", "hr": "HR Specialist",
    "operations": "Operations Specialist", "health": "Healthcare Specialist", "education": "Trainer", "engineering": "Engineer",
    "legal": "Compliance Specialist", "media": "Content Creator", "hospitality": "Hospitality", "crafts": "Technician",
}


def career_level_ar(years: float | None, has_roles: bool, only_training: bool = False) -> str | None:
    if only_training and (years or 0) < 2:
        return "حديث تخرج (تدريب تعاوني)"
    if years is None:
        return None if has_roles else "حديث تخرج"
    if years < 1:
        return "حديث تخرج / مبتدئ"
    if years < 3:
        return "مبتدئ (أقل من ٣ سنوات)"
    if years < 6:
        return "متوسط الخبرة"
    if years < 10:
        return "خبير"
    return "خبير أول"


def to_detail(item: dict, now: datetime) -> dict:
    detail = {k: item.get(k) for k in ("title", "organization", "location", "start", "end", "current", "highlights")}
    detail.update(period=period_ar(item), duration=duration_ar(months_of(item, now)))
    if item.get("kind"):
        detail["kind"] = item["kind"]
    return detail


def _sort_roles(items: list[dict]) -> list[dict]:
    """Most recent first: current roles, then by end date, then by start date."""
    def key(item: dict) -> str:
        return f"{'9999' if item.get('current') else (item.get('end') or item.get('start') or '0000')}|{item.get('start') or ''}"
    return sorted(items, key=key, reverse=True)


def order_roles(roles: list[dict]) -> list[dict]:
    """Work (jobs + internships) first, newest first; then volunteering."""
    return [*_sort_roles([r for r in roles if r.get("kind") != "volunteer"]), *_sort_roles([r for r in roles if r.get("kind") == "volunteer"])]


def target_title(title: str) -> str | None:
    """«Artificial Intelligence Specialist Trainee» -> «Artificial Intelligence Specialist» (a role to apply for)."""
    clean = re.sub(r"^[\s\-–,]+|[\s\-–,]+$", "", re.sub(r"\s+", " ", _INTERN_WORDS.sub(" ", title))).strip()
    return clean if clean and piece_kind(clean) == "title" else None


def heuristic_profile(text: str, now: datetime | None = None, *, file_name: str | None = None, scanned: bool = False) -> dict:
    """Offline ATS-style reader: the profile shown to the candidate and used for matching, plus the ATS report."""
    now = now or datetime.now(timezone.utc)
    sections = split_sections(text)
    all_lines = cv_lines(text)
    experience_lines = lines_of(sections, "experience")
    volunteer_lines = lines_of(sections, "volunteer")
    structured = any(s.kind != "header" for s in sections)
    fallback = [] if structured and (experience_lines or volunteer_lines) else \
        [line for line in all_lines if not DEGREE.search(normalize_arabic(line)) and not _CERTIFICATE.search(normalize_arabic(line))]
    certification_section = lines_of(sections, "certifications")
    training_roles = [r for r in parse_roles(certification_section, "job") if r["kind"] == "internship" and r["start"]]
    roles = order_roles([*parse_roles(experience_lines or fallback, "job"), *training_roles, *parse_roles(volunteer_lines, "volunteer")])
    work = [r for r in roles if r["kind"] != "volunteer"]

    education_lines = lines_of(sections, "education")
    education_items = parse_education(education_lines or [line for line in all_lines if DEGREE.search(normalize_arabic(line))])
    if training_roles:
        certification_lines = [line for line in certification_section if not find_date_range(line)
                               and not any(line.find(d[:20]) >= 0 for r in training_roles for d in r["details"])]
    else:
        certification_lines = certification_section
    certification_items = parse_certifications(certification_lines or [line for line in all_lines if _CERTIFICATE.search(normalize_arabic(line))
                                                                        and not DEGREE.search(normalize_arabic(line))])
    projects = parse_projects(lines_of(sections, "projects"))

    own_summary = re.sub(r"\s+", " ", " ".join(lines_of(sections, "summary"))).strip()
    has_skills_section = any(s.kind == "skills" for s in sections)
    unsectioned = [] if has_skills_section else [line for line in all_lines if not DEGREE.search(normalize_arabic(line))]
    mined = without_noise("\n".join([own_summary, *(d for r in roles for d in r["details"]), *(p["description"] for p in projects), *unsectioned]))
    skills = extract_skills(sections, text, project_tools=tool_skills([t for p in projects for t in p["tools"]]),
                            certification_text="\n".join(c["name"] for c in certification_items), mined_text=mined or None)
    languages = extract_languages(sections, text)
    stated = _YEARS_STATED.search(normalize_arabic(text))
    years = total_years(work, now)
    if years is None and stated and not work:
        years = int(stated.group(1))
    only_training = bool(work) and all(r["kind"] == "internship" for r in work)

    groups: dict[str, int] = {}
    for skill in skills:
        group = skill_group(skill)
        if group and group not in ("soft", "language") and canonical_skill(skill) not in _GENERIC_SKILLS:
            groups[group] = groups.get(group, 0) + 1
    ranked_groups = [g for g, _ in sorted(groups.items(), key=lambda item: -item[1])]
    job_titles = unique_strings([r["title"] for r in work if r["title"]], 6)
    targets = unique_strings([t for t in (r["title"] if r["kind"] == "job" else (target_title(r["title"]) or "") for r in work) if t], 3)
    suggested = unique_strings([t for t in [*targets[:2], *(_ROLE_BY_GROUP.get(g, "") for g in ranked_groups[:4])] if t], 5)
    keywords = unique_strings([k for k in [*targets, *(_ROLE_BY_GROUP.get(g, "") for g in ranked_groups[:3]), *(_ROLE_EN.get(g, "") for g in ranked_groups[:3]),
                                           *[s for s in skills if skill_group(s) != "soft"][:6]] if k], 14)

    education = [format_education(e) for e in education_items]
    latest = work[0] if work else (roles[0] if roles else None)
    months = js_round(years * 12) if years else None
    hard = [s for s in skills if skill_group(s) != "soft"]
    first_line = ""
    if latest and latest["title"]:
        experience_part = f" بخبرة {duration_ar(months)}" if months else ""
        organization_part = f"، آخرها لدى {latest['organization']}" if latest["organization"] else ""
        first_line = f"{latest['title']}{experience_part}{organization_part}."
    skills_line = f"من أبرز المهارات: {'، '.join(hard[:4]) or '، '.join(skills[:4])}." if skills else ""
    generated = " ".join(p for p in [first_line, f"المؤهل: {education[0]}." if education else "", skills_line] if p)
    if own_summary:
        summary = f"{re.sub(r'\s\S*$', '', own_summary[:257])}…" if len(own_summary) > 260 else own_summary
    else:
        summary = generated or "سيرة ذاتية مهنية."

    ats = ats_report(text=text, sections=sections, roles=roles, education=education_items, skills=skills, languages=languages,
                     certifications=len(certification_items), projects=len(projects), has_summary=len(own_summary.split()) >= 12,
                     titles=targets, file_name=file_name, scanned=scanned)
    return {
        "summary": summary, "skills": skills,
        "experience": [format_experience(r, now) for r in roles],
        "experienceDetails": [to_detail(r, now) for r in roles],
        "education": education, "jobTitles": job_titles, "languages": languages,
        "certifications": [format_certification(c) for c in certification_items],
        "suggestedRoles": suggested, "searchKeywords": keywords,
        "careerLevel": career_level_ar(years, bool(roles), only_training), "yearsExperience": years,
        "projects": projects, "ats": ats, "engine": "heuristic",
    }


# ---------------------------------------------------------------- Claude's reading, verified

class _ClaudeRole(BaseModel):
    title: str = Field(description="المسمى كما ورد في السيرة")
    organization: str = Field(description="الجهة كما وردت في السيرة (بدون اسم المدينة)")
    location: str = Field(description="المدينة إن ذُكرت، وإلا نص فارغ")
    kind: Literal["job", "internship", "volunteer"] = Field(description="job وظيفة، internship تدريب تعاوني أو تمهير أو Co-op أو Trainee، volunteer تطوع أو نشاط طلابي")
    start: str = Field(description="YYYY-MM أو YYYY بالتقويم الميلادي (حوّل الهجري)، أو نص فارغ")
    end: str = Field(description='YYYY-MM أو YYYY، أو "present" إن كان مستمرًا، أو نص فارغ')
    highlights: list[str] = Field(description="أهم إنجاز أو إنجازان، بالعربية، بجملة قصيرة تبدأ بفعل، مع الأرقام إن وُجدت")
    evidence: str = Field(description="عبارة قصيرة منقولة حرفيًا من السيرة تثبت هذه الخبرة")


class _ClaudeSkill(BaseModel):
    name: str = Field(description="اسم المهارة الشائع: أدوات بأسمائها (Excel، Python، Figma)، ومفاهيم بالعربية (تحليل البيانات)")
    kind: Literal["technical", "tool", "soft"]
    evidence: str = Field(description="عبارة قصيرة منقولة حرفيًا من السيرة تظهر فيها المهارة")


class _ClaudeEducation(BaseModel):
    degree: str
    institution: str
    year: str = Field(description="سنة التخرج أو نص فارغ")
    gpa: str = Field(description="المعدل كما كُتب أو نص فارغ")


class _ClaudeProject(BaseModel):
    name: str
    tools: list[str] = Field(description="الأدوات والتقنيات المذكورة للمشروع")
    description: str = Field(description="جملة واحدة بالعربية")


class ClaudeCv(BaseModel):
    summary: str = Field(description="ملخص مهني بالعربية في جملتين: من هو مهنيًا، وأقوى ما يميزه")
    experience: list[_ClaudeRole]
    skills: list[_ClaudeSkill]
    education: list[_ClaudeEducation]
    certifications: list[str] = Field(description="كل شهادة بصيغة «الاسم – الجهة المانحة» كما وردت")
    projects: list[_ClaudeProject]
    languages: list[str] = Field(description="اللغات بالعربية، ومنها لغة الإشارة إن ذُكرت")
    suggestedRoles: list[str] = Field(description="٣ إلى ٥ مسميات وظيفية بالعربية تناسبه فعلًا في سوق العمل السعودي")
    searchKeywords: list[str] = Field(description="الكلمات المفتاحية التي يفهرس بها نظام ATS هذه السيرة، بالعربية والإنجليزية")


CLAUDE_PROMPT = """أنت وكيل قراءة السير الذاتية في سَند، منصة توظيف للصم والمكفوفين في السعودية.
اقرأ السيرة كما يقرؤها نظام تتبع المتقدمين (ATS) ومختص توظيف متمرس معًا: استخرج الخبرات والتعليم والمهارات والشهادات والمشاريع واللغات، وافهم المسار المهني وما أنجزه المرشح فعلًا.
الأمانة قبل كل شيء: لا تضف وظيفة أو جهة أو مهارة أو تاريخًا غير موجود في السيرة. لكل خبرة ومهارة انقل عبارة قصيرة حرفيًا من نص السيرة دليلًا عليها؛ إن لم تجد دليلًا فلا تذكرها.
فرّق بين الوظيفة والتدريب التعاوني (Co-op، Tamheer، Trainee) والعمل التطوعي. لا تعدّ اسم الجهة مهارة.
اكتب الإنجازات بعربية فصحى مختصرة مع الأرقام إن وُجدت. أبقِ المسميات وأسماء الجهات كما كُتبت.
في الوظائف المقترحة فكّر في ما يناسب خبرته الفعلية ومستواه، ويمكن أداؤه بتواصل كتابي أو مرئي أو صوتي.
تاريخ اليوم {today}. السيرة الذاتية:

<cv>
{cv}
</cv>"""


def supported_by_text(quote: str, normalized_cv: str) -> bool:
    """Does a quote from Claude really occur in the CV? Tolerates spelling variants and small differences."""
    key = normalize_arabic(quote)
    if len(key) >= 3 and key in normalized_cv:
        return True
    words = [w for w in tokenize(quote) if len(w) > 2]
    if not words:
        return False
    return sum(1 for w in words if w in normalized_cv) / len(words) >= 0.7


def _clean_date(value: str, now: datetime) -> str | None:
    m = re.fullmatch(r"((?:19|20)\d{2})(?:-(0[1-9]|1[0-2]))?", value.strip())
    if not m:
        return None
    return None if int(m.group(1)) > now.year + 1 else value.strip()


def verified_claude_profile(ai: ClaudeCv | dict, cv_text: str, now: datetime | None = None, can_verify: bool = True) -> dict:
    """Keeps only what the CV supports, computes durations itself, and formats like the offline reader."""
    now = now or datetime.now(timezone.utc)
    ai = ai if isinstance(ai, ClaudeCv) else ClaudeCv.model_validate(ai)
    normalized_cv = normalize_arabic(cv_text)

    def ok(*quotes: str) -> bool:
        return not can_verify or any(q and supported_by_text(q, normalized_cv) for q in quotes)

    roles = order_roles([{
        "title": r.title.strip(), "organization": r.organization.strip(), "location": r.location.strip(), "kind": r.kind,
        "start": _clean_date(r.start, now), "end": None if re.search("present|current", r.end, re.I) else _clean_date(r.end, now),
        "current": bool(re.search("present|current", r.end, re.I)),
        "highlights": unique_strings((re.sub(r"\.+$", "", h).strip() for h in r.highlights), 2),
    } for r in ai.experience if ok(r.evidence, f"{r.title} {r.organization}")])
    work = [r for r in roles if r["kind"] != "volunteer"]
    known = set(find_skills(cv_text))
    order = ["technical", "tool", "soft"]
    skills = unique_strings((display_skill(s.name) for s in sorted(
        (s for s in ai.skills if ok(s.evidence, s.name) or canonical_skill(s.name) in known), key=lambda s: order.index(s.kind))), 30)
    years = total_years(work, now)
    return {
        "summary": ai.summary.strip(), "skills": skills,
        "experience": [format_experience(r, now) for r in roles],
        "experienceDetails": [to_detail(r, now) for r in roles],
        "education": unique_strings((format_education({"degree": e.degree, "institution": e.institution,
                                                       "year": (m.group(0) if (m := re.search(r"\d{4}", e.year)) else None), "gpa": e.gpa.strip() or None})
                                     for e in ai.education if ok(e.institution, e.degree)), 5),
        "jobTitles": unique_strings([r["title"] for r in work], 6),
        "languages": unique_strings(ai.languages, 6),
        "certifications": unique_strings((re.sub(r"\s+[–—-]\s+", " · ", c, count=1) for c in ai.certifications if ok(c)), 12),
        "suggestedRoles": unique_strings(ai.suggestedRoles, 5),
        "searchKeywords": unique_strings(ai.searchKeywords, 14),
        "careerLevel": career_level_ar(years, bool(roles), bool(work) and all(r["kind"] == "internship" for r in work)),
        "yearsExperience": years,
        "projects": [{"name": p.name.strip(), "tools": unique_strings(p.tools, 12), "description": p.description.strip()} for p in ai.projects if ok(p.name)][:8],
        "ats": None, "engine": "claude",
    }


def merge_profiles(ai: dict, offline: dict) -> dict:
    """Claude's verified reading first; the offline reader fills the gaps and scores the file for ATS."""
    use_offline_roles = not ai["experienceDetails"] and bool(offline["experienceDetails"])
    ai_canonical = {normalize_arabic(canonical_skill(s)) for s in ai["skills"]}
    skills = unique_strings([*ai["skills"], *(s for s in offline["skills"] if normalize_arabic(canonical_skill(s)) not in ai_canonical)], 30)
    job_titles = offline["jobTitles"] if use_offline_roles else ai["jobTitles"]
    ats = None
    if offline.get("ats"):
        ats = {**offline["ats"], "keywords": unique_strings([*job_titles, *(s for s in skills if skill_group(s) != "soft")], 20)}
    return {
        **ai,
        "summary": ai["summary"] or offline["summary"],
        "skills": skills,
        "experience": offline["experience"] if use_offline_roles else ai["experience"],
        "experienceDetails": offline["experienceDetails"] if use_offline_roles else ai["experienceDetails"],
        "jobTitles": job_titles,
        "education": ai["education"] or offline["education"],
        "certifications": ai["certifications"] or offline["certifications"],
        "languages": unique_strings([*ai["languages"], *offline["languages"]], 6),
        "yearsExperience": offline["yearsExperience"] if use_offline_roles else (ai["yearsExperience"] if ai["yearsExperience"] is not None else offline["yearsExperience"]),
        "careerLevel": offline["careerLevel"] if use_offline_roles else (ai["careerLevel"] or offline["careerLevel"]),
        "suggestedRoles": ai["suggestedRoles"] or offline["suggestedRoles"],
        "searchKeywords": unique_strings([*ai["searchKeywords"], *offline["searchKeywords"]], 16),
        "projects": ai["projects"] or offline["projects"],
        "ats": ats,
    }


def read_profile(text: str, file_name: str | None = None, now: datetime | None = None) -> tuple[dict, dict]:
    """The full reading of one CV: offline ATS reader, then Claude's reading verified against the text (when a key is set).

    Returns (profile, stages) where stages tells what ran: {"read": ..., "ai": ("done"|"skipped"|"failed", detail)}.
    """
    from src.agent.inference.llm import ask_claude, llm_available
    from src.logger import get_logger

    log = get_logger("job_agent.ats.reader")
    now = now or datetime.now(timezone.utc)
    offline = heuristic_profile(text, now, file_name=file_name)
    roles = offline["experienceDetails"]
    counts = {kind: sum(1 for r in roles if r.get("kind") == kind) for kind in ("job", "internship", "volunteer")}
    stages = {"read": ("done", f"{counts['job']} وظيفة، {counts['internship']} تدريب، {counts['volunteer']} تطوع، "
                               f"{len(offline['projects'])} مشروع، {len(offline['skills'])} مهارة، تقييم ATS {offline['ats']['score']}/100")}
    if not llm_available("job_agent"):
        log.info("[FALLBACK] no Claude key for the job agent -> offline ATS reader only")
        stages["ai"] = ("skipped", "يحتاج ANTHROPIC_API_KEY؛ استُخدمت قراءة ATS المحلية وحدها")
        return offline, stages
    try:
        ai = ask_claude(CLAUDE_PROMPT.format(today=now.date().isoformat(), cv=text[:120_000]), ClaudeCv, max_tokens=12000, timeout=180, scope="job_agent")
        verified = verified_claude_profile(ai, text, now)
        log.info("[LLM] CV read by Claude: kept %d/%d roles and %d/%d skills with evidence in the CV",
                 len(verified["experienceDetails"]), len(ai.experience), len(verified["skills"]), len(ai.skills))
        stages["ai"] = ("done", f"اعتُمد {len(verified['experienceDetails'])} خبرة و{len(verified['skills'])} مهارة لها دليل في السيرة، "
                                f"من {len(ai.experience)} خبرة و{len(ai.skills)} مهارة قرأها Claude")
        return merge_profiles(verified, offline), stages
    except Exception as exc:  # noqa: BLE001 - the offline reading is always there
        log.warning("[FALLBACK] Claude reading failed (%s) -> offline ATS reader", type(exc).__name__)
        stages["ai"] = ("failed", f"تعذّرت قراءة Claude ({type(exc).__name__})؛ استُخدمت قراءة ATS المحلية")
        return offline, stages


def read_scanned_pdf(pdf_bytes: bytes, file_name: str | None = None, now: datetime | None = None, *, client=None) -> tuple[dict, dict]:
    """A PDF with almost no text layer (a scanned image): Claude reads the PDF itself. Nothing can be checked
    against a text, so the reading is kept as Claude gives it; the ATS report marks the file as not machine-readable."""
    import base64

    from src.agent.inference.llm import anthropic_client, model_id

    now = now or datetime.now(timezone.utc)
    client = client or anthropic_client(scope="job_agent")
    response = client.messages.parse(
        model=model_id("job_agent"), max_tokens=12000,
        messages=[{"role": "user", "content": [
            {"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": base64.standard_b64encode(pdf_bytes).decode()}},
            {"type": "text", "text": CLAUDE_PROMPT.format(today=now.date().isoformat(), cv="(السيرة في ملف PDF المرفق)")},
        ]}],
        output_format=ClaudeCv,
    )
    if response.stop_reason == "refusal" or response.parsed_output is None:
        raise RuntimeError("no_reading")
    ai = response.parsed_output
    offline = heuristic_profile("", now, file_name=file_name, scanned=True)
    profile = merge_profiles(verified_claude_profile(ai, "", now, can_verify=False), offline)
    stages = {"read": ("done", "صورة ممسوحة: لا نص للقراءة المحلية"),
              "ai": ("done", f"قرأ Claude ملف PDF مباشرة: {len(ai.experience)} خبرة و{len(ai.skills)} مهارة")}
    return profile, stages


def looks_like_cv(profile: dict) -> bool:
    """Not a CV: no role, no education and hardly any skill (a stray «teamwork» in a letter is not enough)."""
    hard = [s for s in profile["skills"] if skill_group(s) != "soft"]
    return bool(profile["experience"] or profile["education"] or len(hard) >= 2)
