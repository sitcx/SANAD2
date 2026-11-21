"""ATS score 0-100: reads the CV the way an Applicant Tracking System does.

Can it find the contact details, the standard sections, every role with dates, measurable
achievements and the skills keywords? Each of the 15 checks comes with a concrete Arabic tip.
"""
from __future__ import annotations

import re

from src.agent.text.arabic import js_round, normalize_arabic, unique_strings

from .experience import place_in
from .sections import Section, cv_lines
from .skills import skill_group

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+", re.ASCII)
_PHONE = re.compile(r"(?:\+|00)?\d[\d\s-]{7,}\d", re.ASCII)
_LINKEDIN = re.compile(r"linkedin\.com/in/[\w%-]+", re.I | re.ASCII)
_PORTFOLIO = re.compile(r"(https?://\S+|\b[\w-]+\.(?:netlify\.app|github\.io|vercel\.app|behance\.net|dribbble\.com|wixsite\.com)\b|github\.com/[\w-]+)", re.I | re.ASCII)


def contact_of(text: str) -> dict:
    top = cv_lines(text)[:8]
    without_email = _EMAIL.sub(" ", text)
    phone = _PHONE.search(re.sub(r"(?:19|20)\d{2}\s*[-–]\s*(?:19|20)\d{2}", " ", without_email))
    city = None
    for line in top:
        city = place_in(_EMAIL.sub(" ", line, count=1))
        if city:
            break
    return {
        "email": bool(_EMAIL.search(text)),
        "phone": bool(phone and len(re.sub(r"\D", "", phone.group(0))) >= 9),
        "city": city,
        "linkedin": bool(_LINKEDIN.search(text)),
        "portfolio": bool(_PORTFOLIO.search(_LINKEDIN.sub(" ", without_email, count=1))),
    }


_EN_VERBS = {"led", "built", "ran", "made", "wrote", "won", "taught", "grew", "drove", "set", "held", "sold", "gave", "kept", "met", "oversaw", "develop",
             "manage", "lead", "analyze", "analyse", "design", "build", "create", "implement", "coordinate", "prepare", "support", "monitor", "conduct",
             "deliver", "train", "mentor", "improve", "maintain", "handle", "resolve", "organize", "organise", "plan", "present", "track", "collaborate",
             "contribute", "propose", "represent", "perform", "provide", "assist", "ensure", "achieve", "increase", "reduce", "launch", "automate",
             "optimize", "serve", "teach", "write", "research", "evaluate", "audit", "review", "negotiate", "process", "operate", "install", "repair",
             "cook", "drive", "care"}
_AR_NOT_VERB = {"في", "من", "على", "علي", "مع", "الى", "إلى", "هو", "هي", "كان", "كانت", "عن", "و"}


def starts_with_action(line: str) -> bool:
    words = line.strip().split()
    first = words[0] if words else ""
    if re.search("[ء-ي]", first):
        return len(first) >= 3 and normalize_arabic(first) not in _AR_NOT_VERB
    word = re.sub("[^a-z-]", "", first.lower())
    if len(word) < 3:
        return False
    return (word in _EN_VERBS or (word.endswith("ed") and len(word) > 4) or (word.endswith("ing") and word[:-3] in _EN_VERBS)
            or (word.endswith("s") and word[:-1] in _EN_VERBS))


def is_quantified(line: str) -> bool:
    """A result with a number («95%», «60+ tickets», «٣٠٪») — not a year or a model name like GPT-4."""
    cleaned = line.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789"))
    cleaned = re.sub(r"\b(?:19|20)\d{2}\b", " ", cleaned, flags=re.ASCII)
    cleaned = re.sub(r"\b[A-Za-z]+[-‑]?\d+[A-Za-z]*\b", " ", cleaned, flags=re.ASCII)
    return bool(re.search(r"\d", cleaned, re.ASCII) or re.search("[%٪]", line))


def _garbage_score(text: str) -> float:
    """Text that did not come out cleanly: symbol runs from tables, icon fonts, broken encodings."""
    length = max(1, len(text))
    junk = len(re.findall("[|]{3,}|\\(cid:\\d+\\)|�|[-]", text))
    singles = len(re.findall(r"(?:^|\s)[A-Za-z](?=\s)(?:\s[A-Za-z](?=\s)){3,}", text))
    return (junk * 20 + singles * 40) / length


def _rate(score: int) -> str:
    return "ممتاز" if score >= 85 else "جيد" if score >= 70 else "مقبول" if score >= 50 else "ضعيف"


def _list_ar(items: list[str]) -> str:
    return "".join(items) if len(items) <= 1 else f"{'، '.join(items[:-1])} و{items[-1]}"


def ats_report(*, text: str, sections: list[Section], roles: list[dict], education: list[dict], skills: list[str], languages: list[str],
               certifications: int, projects: int, has_summary: bool, titles: list[str], file_name: str | None = None,
               scanned: bool = False) -> dict:
    contact = contact_of(text)
    kinds = list(dict.fromkeys(s.kind for s in sections))
    words = len([w for w in text.split() if re.search("[A-Za-zء-ي0-9]", w)])
    bullets = [d for role in roles for d in role.get("details", [])]
    quantified = sum(1 for b in bullets if is_quantified(b))
    action_verbs = sum(1 for b in bullets if starts_with_action(b))
    hard = [s for s in skills if skill_group(s) != "soft"]
    checks: list[dict] = []

    def check(check_id: str, label: str, weight: int, score: float, tip: str) -> None:
        checks.append({"id": check_id, "label": label, "weight": weight, "score": max(0, min(1, js_round(score * 100) / 100)), "tip": tip})

    missing = [name for ok, name in ((contact["email"], "البريد الإلكتروني"), (contact["phone"], "رقم الجوال"), (contact["city"], "المدينة")) if not ok]
    check("contact", "بيانات التواصل", 10, (int(contact["email"]) * 4 + int(contact["phone"]) * 4 + int(bool(contact["city"])) * 2) / 10,
          f"أضف في أعلى السيرة: {_list_ar(missing)}.")
    check("linkedin", "رابط LinkedIn", 3, 1 if contact["linkedin"] else 0, "أضف رابط حسابك في LinkedIn بجانب بيانات التواصل.")
    check("summary", "الملخص المهني", 8, 1 if has_summary else 0, "أضف ملخصًا مهنيًا من سطرين أو ثلاثة يذكر المسمى الذي تستهدفه وأهم مهاراتك.")
    standard = ["experience" in kinds or "volunteer" in kinds, "education" in kinds, "skills" in kinds]
    check("headings", "عناوين الأقسام المعيارية", 10, sum(standard) / 3,
          "استخدم عناوين أقسام يعرفها نظام ATS: «Experience / الخبرات»، «Education / التعليم»، «Skills / المهارات».")
    dated = sum(1 for r in roles if r.get("start") and (r.get("end") or r.get("current")))
    check("dates", "تواريخ الخبرات", 12, dated / len(roles) if roles else 0,
          "اكتب تاريخ البداية والنهاية لكل خبرة بصيغة واحدة واضحة، مثل: Feb 2026 – Aug 2026 أو 2022 – الآن." if roles
          else "أضف قسم الخبرات (عمل أو تدريب تعاوني أو تطوع) مع تاريخ كل خبرة.")
    clear = sum(1 for r in roles if r.get("title") and r.get("organization"))
    check("roles", "وضوح المسمى والجهة", 8, clear / len(roles) if roles else 0, "اكتب لكل خبرة المسمى الوظيفي ثم اسم الجهة في سطر واحد، مثل: «Data Analyst – Almarai».")
    check("quantified", "إنجازات بالأرقام", 10, min(1, quantified / len(bullets) / 0.4) if bullets else 0,
          "أضف أرقامًا لإنجازاتك (نسبة، عدد، مبلغ، مدة)، مثل: «رفعت دقة التقارير ٢٠٪» أو «Resolved 60+ tickets daily».")
    check("verbs", "أفعال إنجاز", 6, min(1, action_verbs / len(bullets) / 0.7) if bullets else 0,
          "ابدأ كل نقطة بفعل إنجاز: Developed، Analyzed، Led — أو: طوّرت، حلّلت، قدت.")
    check("skills", "الكلمات المفتاحية للمهارات", 12, min(1, len(hard) / 8) * 0.8 + (0.2 if "skills" in kinds else 0),
          "أضف قسم مهارات يذكر الأدوات والبرامج بأسمائها كما تكتبها إعلانات الوظائف (مثل Excel، SQL، Python، Power BI).")
    full_education = any(e.get("degree") and e.get("institution") for e in education)
    check("education", "المؤهل العلمي", 6, 1 if full_education else 0.5 if education else 0, "اذكر المؤهل والتخصص والجامعة وسنة التخرج.")
    check("length", "طول السيرة", 6, 1 if 250 <= words <= 900 else 0.5 if 150 <= words <= 1300 else 0,
          "سيرتك قصيرة؛ أضف تفاصيل خبراتك ومشاريعك وإنجازاتك." if words < 250 else "سيرتك طويلة؛ اختصرها إلى صفحة أو صفحتين بأهم ما يخص الوظيفة.")
    garbage = _garbage_score(text)
    check("readable", "قابلية القراءة الآلية", 9, 0 if scanned else 1 if garbage < 0.002 else 0.5 if garbage < 0.01 else 0,
          "الملف صورة ممسوحة ولا تقرؤه أنظمة ATS. صدّر سيرتك من Word أو Google Docs بصيغة PDF نصية." if scanned
          else "تجنّب الجداول والأعمدة والرموز والأيقونات؛ أنظمة ATS تقرأ النص بالترتيب فقط.")
    check("languages", "اللغات", 3, 1 if languages else 0, "أضف قسم اللغات مع المستوى، مثل: العربية — اللغة الأم، الإنجليزية — متقدم.")
    check("certifications", "الشهادات والدورات", 3, 1 if certifications else 0, "أضف الشهادات المهنية والدورات المعتمدة إن وُجدت.")
    extension = (file_name or "").lower().rsplit(".", 1)[-1] if file_name else ""
    check("file", "نوع الملف", 4, 1 if not extension or extension in ("pdf", "docx") else 0.5, "احفظ السيرة بصيغة PDF نصية أو DOCX بدل DOC القديمة.")

    total = sum(c["weight"] for c in checks)
    score = js_round(sum(c["weight"] * c["score"] for c in checks) / total * 100)
    tips = [c["tip"] for c in sorted((c for c in checks if c["score"] < 1), key=lambda c: -(1 - c["score"]) * c["weight"])][:6]
    return {
        "score": score, "rating": _rate(score), "checks": checks, "tips": tips,
        "keywords": unique_strings([*titles, *hard], 20), "contact": contact,
        "sections": [k for k in kinds if k not in ("header", "other")],
        "stats": {"words": words, "bullets": len(bullets), "quantified": quantified, "actionVerbs": action_verbs, "roles": len(roles)},
    }
