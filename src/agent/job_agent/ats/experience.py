"""Reads work experience the way an ATS does.

Each role gets title, organisation, city, start/end dates, kind (job / internship / volunteer) and
achievements. Durations are computed from the dates (never guessed) and written in Arabic.
Roles are plain dicts: {title, organization, location, start, end, current, highlights, kind, details}.
"""
from __future__ import annotations

import re
from datetime import datetime

from src.agent.text.arabic import ar_digits, js_round, normalize_arabic, to_ascii_digits, unique_strings

A = re.ASCII   # JavaScript regexes (no /u flag): \b, \w and \d are ASCII-only
I = re.I | re.ASCII

_MONTHS = {
    "يناير": 1, "فبراير": 2, "مارس": 3, "ابريل": 4, "مايو": 5, "يونيو": 6, "يونيه": 6, "يوليو": 7, "يوليه": 7, "اغسطس": 8, "سبتمبر": 9,
    "اكتوبر": 10, "نوفمبر": 11, "ديسمبر": 12, "كانون الثاني": 1, "شباط": 2, "اذار": 3, "نيسان": 4, "ايار": 5, "حزيران": 6, "تموز": 7,
    "اب": 8, "ايلول": 9, "تشرين الاول": 10, "تشرين الثاني": 11, "كانون الاول": 12,
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6, "july": 7, "august": 8, "september": 9, "october": 10,
    "november": 11, "december": 12, "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7, "aug": 8, "sep": 9, "sept": 9, "oct": 10,
    "nov": 11, "dec": 12,
}
_MONTH_ALT = ("يناير|فبراير|مارس|أبريل|ابريل|إبريل|مايو|يونيو|يونيه|يوليو|يوليه|أغسطس|اغسطس|سبتمبر|أكتوبر|اكتوبر|نوفمبر|ديسمبر|كانون الثاني|شباط|آذار"
              "|اذار|نيسان|أيار|ايار|حزيران|تموز|آب|أيلول|ايلول|تشرين الأول|تشرين الاول|تشرين الثاني|كانون الأول|كانون الاول|january|february|march"
              "|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sept|sep|oct|nov|dec")
_PRESENT = ("حتى الآن|حتى الان|إلى الآن|الى الآن|الى الان|الآن|الان|حالياً|حاليًا|حاليا|للآن|لا يزال|مستمر|present|currently|current|now|today"
            "|to date|till date|ongoing")
_DATE = rf"(?:(?:{_MONTH_ALT})\.?,?\s+\d{{4}}|\d{{1,2}}\s*[/.-]\s*\d{{4}}|\d{{4}}\s*[/.-]\s*\d{{1,2}}(?!\d)|1[34]\d{{2}}\s*هـ?|(?:19|20)\d{{2}})"
_RANGE = re.compile(rf"(?:(?:من|from)\s+)?({_DATE})\s*(?:-|–|—|~|to|until|till|إلى|الى|حتى)\s*({_DATE}|{_PRESENT})|(?:منذ|since)\s+({_DATE})", I)
_NAMED = re.compile(rf"^({_MONTH_ALT})\s+(\d{{4}})$", I)


def _parse_date(raw: str) -> tuple[int, int | None] | None:
    text = re.sub(r"\s+", " ", re.sub(r"[.,]", " ", normalize_arabic(raw))).strip()
    if m := re.match(r"^(1[34]\d{2})\s*ه", text, A):
        return js_round(int(m.group(1)) * 0.970229 + 621.5643), None
    if (m := _NAMED.match(text)) and m.group(1).lower() in _MONTHS:
        return int(m.group(2)), _MONTHS[m.group(1).lower()]
    if m := (re.match(r"^(\d{1,2})\s*[/.-]\s*(\d{4})$", text, A) or re.match(r"^(\d{1,2})\s+(\d{4})$", text, A)):
        return int(m.group(2)), min(12, max(1, int(m.group(1))))
    if m := re.match(r"^(\d{4})\s*[/.-]\s*(\d{1,2})$", text, A):
        return int(m.group(1)), min(12, max(1, int(m.group(2))))
    if m := re.match(r"^((?:19|20)\d{2})$", text, A):
        return int(m.group(1)), None
    return None


def _serialize(value: tuple[int, int | None] | None) -> str | None:
    if not value:
        return None
    year, month = value
    return f"{year}-{month:02d}" if month else str(year)


def _deserialize(value: str | None) -> tuple[int, int | None] | None:
    if not value:
        return None
    parts = value.split("-")
    year = int(parts[0]) if parts[0].isdigit() else 0
    month = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None
    return (year, month or None) if year else None


def find_date_range(line: str) -> dict | None:
    """{start, end, current, text} for «Mar 2023 – Present», «06/2021 - 02/2023», «من 1440هـ إلى 1445هـ», «منذ 2019»…"""
    m = _RANGE.search(to_ascii_digits(line))
    if not m:
        return None
    if m.group(3):
        return {"start": _serialize(_parse_date(m.group(3))), "end": None, "current": True, "text": m.group(0)}
    start, end = _parse_date(m.group(1)), _parse_date(m.group(2))
    if not start:
        return None
    return {"start": _serialize(start), "end": _serialize(end), "current": not end, "text": m.group(0)}


def months_of(item: dict, now: datetime) -> int | None:
    """Months between two dates (inclusive of the start month); None when only one year is known."""
    start = _deserialize(item.get("start"))
    if not start:
        return None
    end = (now.year, now.month) if item.get("current") else _deserialize(item.get("end"))
    if not end:
        return None
    if start[1] and end[1]:
        return max(1, (end[0] - start[0]) * 12 + (end[1] - start[1]) + 1)
    years = end[0] - start[0]
    return years * 12 if years > 0 else None


def _years_ar(years: int) -> str:
    return "سنة" if years == 1 else "سنتان" if years == 2 else f"{ar_digits(years)} سنوات" if years <= 10 else f"{ar_digits(years)} سنة"


def _months_ar(months: int) -> str:
    return "شهر" if months == 1 else "شهران" if months == 2 else f"{ar_digits(months)} أشهر" if months <= 10 else f"{ar_digits(months)} شهرًا"


def duration_ar(months: int | None) -> str:
    if not months or months < 1:
        return ""
    years, rest = divmod(months, 12)
    if not years:
        return _months_ar(rest)
    return f"{_years_ar(years)} و{_months_ar(rest)}" if rest else _years_ar(years)


_MONTH_NAMES_AR = ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو", "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"]


def _date_ar(value: str | None) -> str:
    parsed = _deserialize(value)
    if not parsed:
        return ""
    return f"{_MONTH_NAMES_AR[parsed[1] - 1]} {ar_digits(parsed[0])}" if parsed[1] else ar_digits(parsed[0])


def period_ar(item: dict) -> str:
    """«مارس ٢٠٢٣ – الآن»."""
    start = _date_ar(item.get("start"))
    if not start:
        return ""
    if item.get("current"):
        return f"{start} – الآن"
    end = _date_ar(item.get("end"))
    return f"{start} – {end}" if end and end != start else start


INTERN = re.compile(r"(trainee|intern\b|internship|co-?op\b|cooperative|apprentice|متدرب|تدريب تعاوني|تدريب ميداني|تمهير|summer training)", I)


def format_experience(item: dict, now: datetime) -> str:
    """One line per role, like the dashboard: «المسمى · الجهة · المدة» (no raw dates)."""
    parts = [item.get("title", ""), item.get("organization", ""), duration_ar(months_of(item, now))]
    if item.get("kind") == "volunteer":
        parts.append("تطوعي")
    elif item.get("kind") == "internship" and not INTERN.search(normalize_arabic(item.get("title", ""))):
        parts.append("تدريب")
    return " · ".join(p for p in parts if p)


def total_years(items: list[dict], now: datetime) -> float | None:
    """Total experience without double-counting overlapping roles, in years (one decimal)."""
    intervals = []
    for item in items:
        start, months = _deserialize(item.get("start")), months_of(item, now)
        if not start or not months:
            continue
        begin = start[0] * 12 + (start[1] or 1) - 1
        intervals.append((begin, begin + months))
    if not intervals:
        return None
    intervals.sort()
    total, (cur_start, cur_end) = 0, intervals[0]
    for begin, end in intervals[1:]:
        if begin <= cur_end:
            cur_end = max(cur_end, end)
        else:
            total += cur_end - cur_start
            cur_start, cur_end = begin, end
    total += cur_end - cur_start
    return js_round(total / 12 * 10) / 10


# ---------------------------------------------------------------- the parts of a role

BULLET = re.compile(r"^[•·▪●◦○■□➢➤►✓✔✗*\-–]\s*")
_SENTENCE_END = re.compile(r"[.!?؟]$")
_SMALL_WORDS = {"of", "and", "the", "for", "in", "at", "on", "to", "with", "a", "an", "de", "by", "from", "via", "as"}
_TITLE_HEADS_EN = {"analyst", "designer", "developer", "engineer", "accountant", "specialist", "assistant", "manager", "technician", "teacher", "trainer", "clerk",
                   "officer", "coordinator", "representative", "consultant", "agent", "operator", "supervisor", "intern", "trainee", "nurse", "doctor",
                   "physician", "pharmacist", "lead", "head", "director", "administrator", "executive", "associate", "programmer", "architect", "cashier",
                   "receptionist", "secretary", "member", "chair", "chairman", "chairperson", "president", "volunteer", "leader", "ambassador", "founder",
                   "co-founder", "mentor", "tutor", "instructor", "researcher", "scientist", "writer", "editor", "translator", "interpreter", "advisor",
                   "adviser", "planner", "auditor", "controller", "buyer", "driver", "chef", "cook", "barista", "waiter", "guard", "worker", "apprentice",
                   "fellow", "partner", "owner", "freelancer", "tester", "strategist", "marketer", "recruiter", "therapist", "dentist", "paralegal", "lawyer",
                   "secretary-general", "organizer", "organiser", "moderator", "captain", "treasurer", "delegate"}
_ORG_HEADS_EN = {"company", "corp", "corporation", "bank", "ministry", "authority", "university", "college", "hospital", "clinic", "center", "centre", "group",
                 "inc", "ltd", "llc", "co", "foundation", "association", "agency", "school", "hotel", "factory", "store", "club", "committee", "team",
                 "council", "society", "institute", "academy", "organization", "organisation", "department", "office", "program", "programme", "initiative",
                 "lab", "laboratory", "studio", "firm", "bureau", "commission", "fund", "network", "community", "union", "federation", "chamber", "holding",
                 "holdings", "solutions", "services", "systems", "technologies", "technology", "consulting", "partners", "bookstore", "pharmacy", "airlines",
                 "airways", "telecom", "municipality", "court", "embassy", "platform", "project", "museum", "library", "hub"}
_TITLE_HEADS_AR = ["محلل", "مصمم", "مطور", "مبرمج", "مهندس", "محاسب", "اخصائي", "مساعد", "مدير", "موظف", "فني", "معلم", "مدرس", "مدرب", "سكرتير", "كاشير",
                   "مندوب", "منسق", "مشرف", "ممثل", "باحث", "كاتب", "مدخل", "متدرب", "ممرض", "طبيب", "صيدلي", "مستشار", "رئيس", "قائد", "امين", "مراقب",
                   "مسؤول", "مسئول", "خبير", "استشاري", "عضو", "متطوع", "نائب", "مؤسس", "مرشد", "مترجم", "محرر", "سفير", "مدقق", "مصور", "طاه", "سائق",
                   "حارس", "عامل", "بائع", "مستقبل", "منظم"]
_ORG_HEADS_AR = ["شركه", "مؤسسه", "بنك", "مصرف", "وزاره", "هيئه", "جامعه", "كليه", "معهد", "مستشفي", "مستوصف", "مركز", "مجموعه", "جمعيه", "مكتب", "مدرسه",
                 "امانه", "بلديه", "اداره", "مجمع", "مصنع", "متجر", "فندق", "مطعم", "نادي", "لجنه", "فريق", "مجلس", "برنامج", "مبادره", "اكاديميه",
                 "صندوق", "منصه", "مكتبه", "صيدليه", "عياده", "محكمه", "سفاره", "قسم", "وكاله", "مختبر", "معرض", "مشروع"]
TITLE_ANY = re.compile(r"(محلل|مصمم|مطور|مبرمج|مهندس|محاسب|اخصائي|مساعد|مدير|موظف|فني|معلم|مدرب|سكرتير|كاشير|مندوب|منسق|مشرف|ممثل|باحث|كاتب|مدخل|متدرب|ممرض|طبيب"
                       r"|صيدلي|مستشار|رئيس|قائد|امين|مراقب|مسؤول|خبير|استشاري|analyst|designer|developer|engineer|accountant|specialist|assistant|manager"
                       r"|technician|teacher|trainer|clerk|officer|coordinator|representative|consultant|agent|operator|supervisor|intern|trainee|nurse|doctor"
                       r"|pharmacist|director|administrator|executive|associate|programmer|architect|cashier|receptionist|secretary)", I)
ORG_ANY = re.compile(r"(شركه|مؤسسه|بنك|مصرف|وزاره|هيئه|جامعه|كليه|معهد|مستشفي|مستوصف|مركز|مجموعه|جمعيه|مكتب|مدرسه|امانه|بلديه|اداره|مجمع|مصنع|متجر|فندق|مطعم"
                     r"|\bcompany\b|\bcorp|\bbank\b|\bministry\b|\bauthority\b|\buniversity\b|\bcollege\b|\bhospital\b|\bclinic\b|\bcent(er|re)\b|\bgroup\b"
                     r"|\binc\b|\bltd\b|\bllc\b|\bfoundation\b|\bassociation\b|\bagency\b|\bschool\b|\bhotel\b|\bclub\b|\bcommittee\b|\binstitute\b|\bacademy\b)", I)

_PLACES = list(dict.fromkeys([
    "الرياض", "جده", "الدمام", "مكه", "مكه المكرمه", "المدينه", "المدينه المنوره", "الخبر", "الظهران", "الطائف", "تبوك", "ابها", "القصيم", "بريده", "عنيزه",
    "حائل", "جازان", "جيزان", "نجران", "الاحساء", "الهفوف", "الجبيل", "ينبع", "الباحه", "عرعر", "سكاكا", "الجوف", "خميس مشيط", "القطيف", "حفر الباطن",
    "الخرج", "المنطقه الشرقيه", "نيوم", "العلا",
    "riyadh", "jeddah", "jiddah", "dammam", "makkah", "mecca", "madinah", "medina", "al madinah", "khobar", "al khobar", "alkhobar", "dhahran", "taif",
    "tabuk", "abha", "qassim", "al qassim", "buraidah", "buraydah", "hail", "jazan", "jizan", "najran", "al ahsa", "al-ahsa", "ahsa", "hofuf", "jubail",
    "yanbu", "al baha", "arar", "sakaka", "khamis mushait", "qatif", "hafar al-batin", "al kharj", "eastern province", "neom", "alula",
    "saudi arabia", "kingdom of saudi arabia", "ksa", "sa", "السعوديه", "المملكه العربيه السعوديه", "المملكه",
    "uae", "united arab emirates", "الامارات", "dubai", "دبي", "abu dhabi", "ابوظبي", "qatar", "قطر", "doha", "الدوحه", "kuwait", "الكويت", "bahrain",
    "البحرين", "manama", "المنامه", "oman", "عمان", "muscat", "مسقط", "egypt", "مصر", "cairo", "القاهره", "jordan", "الاردن", "amman", "usa",
    "united states", "uk", "united kingdom", "london", "canada", "australia", "malaysia", "india", "pakistan",
    "remote", "hybrid", "on-site", "onsite", "عن بعد", "هجين", "حضوري",
]))
_PLACE_SET = set(_PLACES)
_NOT_CITY = {"saudi arabia", "kingdom of saudi arabia", "ksa", "sa", "السعوديه", "المملكه العربيه السعوديه", "المملكه", "remote", "hybrid", "on-site",
             "onsite", "عن بعد", "هجين", "حضوري", "uae", "usa", "uk"}
_CITIES = sorted((p for p in _PLACES if p not in _NOT_CITY), key=len, reverse=True)


def is_place(piece: str) -> bool:
    """«Saudi Arabia, Riyadh» / «الرياض» / «Remote»: made only of places."""
    parts = [re.sub(r"\.+$", "", normalize_arabic(p)).strip() for p in re.split(r"[,،|/–—()·]|\s-\s", piece)]
    parts = [p for p in parts if p]
    return bool(parts) and all(p in _PLACE_SET for p in parts)


def _title_case(value: str) -> str:
    return re.sub(r"(^|\s)([a-z])", lambda m: m.group(1) + m.group(2).upper(), value)


def place_in(line: str) -> str | None:
    """The city (or country) named in a line: a separated piece first, else a known city anywhere in it."""
    for part in (p.strip() for p in re.split(r"[,،|/–—·]|\s-\s", line)):
        if part and is_place(part):
            return part
    padded = f" {normalize_arabic(line)} "
    city = next((c for c in _CITIES if f" {c} " in padded), None)
    return _title_case(city) if city else None


def _title_case_ratio(line: str, small: set[str] = _SMALL_WORDS) -> float:
    words = [re.sub(r"^[^A-Za-z]+|[^A-Za-z]+$", "", w) for w in line.split()]
    words = [w for w in words if re.search("[A-Za-z]", w) and w.lower() not in small]
    return sum(1 for w in words if re.match("[A-Z]", w)) / len(words) if words else 0


def piece_kind(piece: str) -> str | None:
    """What a piece names: a job 'title', an 'org', a 'place', or None — read from its head noun."""
    if is_place(piece):
        return "place"
    key = re.sub(r"\s+", " ", normalize_arabic(re.sub(r"\([^)]*\)", " ", piece))).strip()
    if not key:
        return None
    if re.search("[a-z]", key) and not re.search("[ء-ي]", key):
        core = re.split(r"\s+(?:of|for|at|in|and|&)\s+|\s[-–—|]\s", key)[0].strip()
        words = [w for w in re.split(r"[\s/]+", core) if w]
        head, first = (words[-1] if words else ""), (words[0] if words else "")
        if head in _TITLE_HEADS_EN:
            return "title"
        if head in _ORG_HEADS_EN or first in _ORG_HEADS_EN:
            return "org"
        if any(w in _ORG_HEADS_EN for w in words):
            return "org"
        if any(w in _TITLE_HEADS_EN for w in words):
            return "title"
        return None
    first = key.split()[0] if key.split() else ""
    stem = re.sub(r"(ه|ات|ين|ون)$", "", re.sub(r"^(ال|و)", "", first))
    if any(first == w or first == f"ال{w}" for w in _ORG_HEADS_AR) or first == "مديريه":
        return "org"
    if any(stem == w or first == w or stem.startswith(w) for w in _TITLE_HEADS_AR):
        return "title"
    if stem in _ORG_HEADS_AR:
        return "org"
    if ORG_ANY.search(key):
        return "org"
    if TITLE_ANY.search(key):
        return "title"
    return None


def clean_part(part: str) -> str:
    value = re.sub(r"\s+", " ", re.sub(r"^[\s\-–—|·:،,]+|[\s\-–—|·:،,]+$", "", BULLET.sub("", part, count=1))).strip()
    if value.startswith("(") and ")" not in value:
        value = value[1:].strip()
    if value.endswith(")") and "(" not in value:
        value = value[:-1].strip()
    if value.count("(") > value.count(")"):
        value = f"{value})"
    return value


SPLIT_HEADER = re.compile(r"\s+[-–—|·•]\s+|\s*[|·•]\s*|\s+(?:at|@|لدى|لدي)\s+|\s+في\s+(?=(?:شركة|شركه|مؤسسة|مؤسسه|بنك|وزارة|وزاره|هيئة|هيئه|جامعة|جامعه|مستشفى"
                          r"|مستشفي|مركز|مجموعة|مجموعه|جمعية|جمعيه))|\s*،\s*|,\s*(?![^(]*\))", I)


def _header_pieces(part: str) -> list[str]:
    pieces = [clean_part(p) for p in SPLIT_HEADER.split(part)]
    return [p for p in pieces if 2 <= len(p) <= 90 and not re.fullmatch(r"\d+", p) and not re.fullmatch(r"(خبره|خبرة|experience)", normalize_arabic(p), I)]


def split_header(parts: list[str]) -> dict:
    """«Title - Organisation, Program» / «محلل بيانات - شركة المراعي - الرياض» -> title, organization, location."""
    lines = [line for line in (_header_pieces(p) for p in parts) if line]
    title_line = next((i for i, line in enumerate(lines) if any(piece_kind(p) == "title" for p in line)), -1)
    if len(lines) >= 2 and 0 <= title_line < len(lines) - 1:
        own = lines[title_line]
        title_at = next(i for i, p in enumerate(own) if piece_kind(p) == "title")
        after = [p for p in own[title_at + 1:] if piece_kind(p) != "place"]
        below = [p for line in lines[title_line + 1:] for p in line]
        below_org = next((p for p in below if piece_kind(p) not in ("place", "title")), None)
        organization = below_org or next((p for p in after if piece_kind(p) == "org"), None) or (after[0] if after else "")
        qualifiers = [p for p in after if piece_kind(p) != "org"] if below_org else []
        location = next((p for p in [*below, *own] if piece_kind(p) == "place"), "")
        return {"title": "، ".join([own[title_at], *qualifiers]), "organization": organization, "location": location}
    pieces = [p for line in lines for p in line]
    kinds = [piece_kind(p) for p in pieces]
    title_at = kinds.index("title") if "title" in kinds else -1
    org_at = next((i for i, k in enumerate(kinds) if k == "org" and i != title_at), -1)
    place_at = kinds.index("place") if "place" in kinds else -1
    free = [i for i, k in enumerate(kinds) if k is None]
    if title_at < 0:
        title_at = free.pop(0) if free else -1
    elif org_at < 0:
        nxt = next((i for i in free if i > title_at), None)
        if nxt is not None:
            org_at = nxt
            free.remove(nxt)
    if org_at < 0:
        org_at = next((i for i in free if i != title_at), -1)
    extras = [] if org_at < 0 else [i for i in range(len(pieces)) if i > org_at and i not in (title_at, place_at)
                                    and kinds[i] in ("org", None) and len(pieces[i].split(" ")) <= 6]
    return {
        "title": pieces[title_at] if title_at >= 0 else "",
        "organization": "، ".join([pieces[org_at], *(pieces[i] for i in extras)]) if org_at >= 0 else "",
        "location": pieces[place_at] if place_at >= 0 else "",
    }


def _separate_description(organization: str) -> tuple[str, str]:
    """«مستشفى الملك فهد بالدمام في رعاية المرضى» -> organisation + the description that followed it."""
    if len(organization.split(" ")) <= 5:
        return organization, ""
    cut = re.search(r"\s(?:في|حيث|where|working on|responsible for)\s", organization, I)
    if not cut or cut.start() < 4:
        return organization, ""
    return organization[:cut.start()].strip(), re.sub(r"^\s*(?:في|حيث)\s*", "", organization[cut.start():]).strip()


DEGREE = re.compile(r"(بكالوريوس|بكالريوس|ماجستير|دكتوراه|دبلوم|ثانوي|ثانويه|bachelor|master|phd|diploma|degree|b\.?sc|m\.?sc|\bba\b|\bma\b|mba|high school)", I)


def _looks_like_header(line: str) -> bool:
    """Short, not a sentence, mostly Title Case (English) or led by a title/organisation word (Arabic)."""
    if BULLET.search(line) or len(line) < 3 or len(line) > 130 or _SENTENCE_END.search(line) or re.match("[a-z]", line):
        return False
    words = len(line.split())
    if re.search("[A-Za-z]", line) and not re.search("[ء-ي]", line):
        return words <= 16 and _title_case_ratio(line) >= 0.6
    if words > 14:
        return False
    kind = piece_kind(SPLIT_HEADER.split(line)[0])
    norm = normalize_arabic(line)
    return kind in ("title", "org") or bool(re.search(r"\s[-–—|]\s|،", line) and (TITLE_ANY.search(norm) or ORG_ANY.search(norm)))


def _is_list(line: str) -> bool:
    """A comma list of short items («BLS, ACLS, مكافحة العدوى») — not an achievement."""
    items = [i.strip() for i in re.split("[,،;|]", line) if i.strip()]
    return len(items) >= 3 and all(len(i.split()) <= 4 for i in items)


def _classify(line: str, previous: tuple[str, str] | None) -> tuple[str, dict | None]:
    bullet = bool(BULLET.search(line))
    found = find_date_range(line)
    if found and not (bullet and previous):
        rest = BULLET.sub("", to_ascii_digits(line).replace(found["text"], " ", 1), count=1)
        meaningful = [p.strip() for p in re.split(r"[,،|·()\-–—:]", rest)]
        meaningful = [p for p in meaningful if p and not is_place(p) and re.search("[A-Za-zء-ي]{2}", p)]
        return ("inline" if meaningful else "date"), found
    if bullet:
        return "bullet", None
    if is_place(line) and len(line) <= 60:
        return "place", None
    if re.match("[a-z]", line):
        if previous and previous[0] == "header" and len(line.split()) <= 6 and not _SENTENCE_END.search(line):
            return "header", None
        return "continuation", None
    if previous and previous[0] in ("bullet", "text", "continuation") and not _SENTENCE_END.search(previous[1]) and not _looks_like_header(line):
        return "continuation", None
    if _looks_like_header(line):
        return "header", None
    return "text", None


def _role_kind(title: str, organization: str, section_kind: str) -> str:
    if section_kind == "volunteer":
        return "volunteer"
    key = normalize_arabic(f"{title} {organization}")
    if re.search(r"(volunteer|متطوع|تطوعي)", key, I):
        return "volunteer"
    return "internship" if INTERN.search(key) else section_kind


def parse_roles(lines: list[str], section_kind: str = "job") -> list[dict]:
    """Roles from an experience section (or the whole CV), whatever the layout: one-line roles, title / organisation /
    date on separate lines, the date before or after the header, or between the achievements (two-column PDFs)."""
    blocks: list[dict] = []
    current: dict | None = None
    loose: list[str] = []
    previous: tuple[str, str] | None = None

    def start(header: list[str], found: dict | None) -> dict:
        nonlocal current, loose
        current = {"header": header, "range": found, "location": "", "details": []}
        blocks.append(current)
        loose = []
        return current

    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        kind, found = _classify(line, previous)
        block = current
        if kind == "inline":
            without_date = BULLET.sub("", to_ascii_digits(line), count=1).replace(found["text"], " ", 1)
            head, *desc_parts = re.split(r"[:：]\s+", without_date)
            description = ": ".join(desc_parts).strip()
            if block and not block["range"] and not block["details"] and block["header"]:
                block["header"].append(head)
                block["range"] = found
                if description:
                    block["details"].append(description)
            else:
                created = start([*([] if block else loose[-2:]), head], found)
                if description:
                    created["details"].append(description)
        elif kind == "date":
            if block and not block["range"]:
                block["range"] = found
                block["location"] = block["location"] or (place_in(line) or "")
            else:
                start([] if block else loose[-2:], found)["location"] = place_in(line) or ""
        elif kind == "place":
            if block and not block["location"]:
                block["location"] = line
        elif kind == "header":
            full_role = piece_kind(SPLIT_HEADER.split(line)[0]) == "title" and bool(SPLIT_HEADER.search(line))
            if block and not block["details"] and len(block["header"]) < 2 and not (block["header"] and block["range"] and full_role):
                block["header"].append(line)
            else:
                start([line], None)
        elif kind == "bullet":
            if block:
                block["details"].append(clean_part(line))
        elif kind == "continuation":
            if block and block["details"]:
                block["details"][-1] = f"{block['details'][-1]} {line}"
            elif block and block["header"]:
                block["header"][-1] = f"{block['header'][-1]} {line}"
        elif kind == "text":
            if block:
                if not _is_list(line):
                    block["details"].append(line)
            elif len(line) <= 90:
                loose.append(line)
                if len(loose) > 3:
                    loose.pop(0)
        previous = (kind, line)

    roles = []
    for block in blocks:
        header = split_header(block["header"])
        organization, description = _separate_description(header["organization"])
        details = unique_strings((re.sub(r"\.+$", "", d) for d in (clean_part(x) for x in [description, *block["details"]]) if len(d) >= 6), 12)
        found = block["range"] or {}
        role = {
            "title": header["title"], "organization": organization, "location": header["location"] or block["location"],
            "start": found.get("start"), "end": found.get("end"), "current": bool(found.get("current")),
            "highlights": [f"{re.sub(r'\s\S*$', '', d[:127])}…" if len(d) > 130 else d for d in details[:3]],
            "details": details, "kind": _role_kind(header["title"], organization, section_kind),
        }
        if (role["start"] and (role["title"] or role["organization"])) or (role["title"] and role["organization"] and piece_kind(role["title"]) == "title"):
            roles.append(role)
    return roles


def parse_experience(lines: list[str], section_kind: str = "job") -> list[dict]:
    return [{k: v for k, v in role.items() if k != "details"} for role in parse_roles(lines, section_kind)]


# ---------------------------------------------------------------- education

_INSTITUTION = re.compile(r"(جامعه|كليه|معهد|مدرسه|ثانويه|اكاديميه|university|college|institute|school|academy|polytechnic)", I)
_GPA = re.compile(r"(?:\b(?:c?gpa)\b|المعدل(?: التراكمي)?|معدل)\s*(?:of|:|=)?\s*(\d+(?:[.,]\d+)?)(?:\s*(?:/|out of|من)\s*(\d+(?:[.,]\d+)?))?", I)
_YEAR_SPAN = re.compile(r"\(?\s*(?:19|20)\d{2}\s*(?:[-–—]\s*(?:(?:19|20)\d{2}|الآن|present))?\s*\)?", I)
_EDU_SPLIT = re.compile(r"\s+[-–—|·•]\s+|\s*[|·•،,]\s*|\s+(?:from|at|من)\s+(?=(?:جامعة|جامعه|كلية|كليه|معهد|university|college|institute))", I)


def _gpa_text(m: re.Match) -> str:
    return f"{m.group(1)}/{m.group(2)}" if m.group(2) else m.group(1)


def _range_year(found: dict) -> str | None:
    if found["current"]:
        return None
    value = found["end"] or found["start"]
    return value[:4] if value else None


def parse_education(lines: list[str]) -> list[dict]:
    out: list[dict] = []
    current: dict | None = None
    for raw in lines:
        line = raw.strip()
        key = normalize_arabic(line)
        bullet = bool(BULLET.search(line))
        ascii_line = to_ascii_digits(line)
        gpa = _GPA.search(ascii_line)
        found = find_date_range(line)
        years = re.findall(r"(?:19|20)\d{2}", ascii_line)
        text = ascii_line.replace(found["text"] if found else "§", " ", 1)
        text = _YEAR_SPAN.sub(" ", _GPA.sub(" ", text, count=1))
        parts = [p for p in (clean_part(x) for x in _EDU_SPLIT.split(text)) if len(p) >= 2]
        degree = next((p for p in parts if DEGREE.search(normalize_arabic(p))), "") if (not bullet or DEGREE.search(key)) else ""
        institution = "" if bullet else next((p for p in parts if p != degree and _INSTITUTION.search(normalize_arabic(p))), "")
        if degree:
            current = {"degree": degree, "institution": institution,
                       "year": _range_year(found) if found else (years[-1] if years else None),
                       "gpa": _gpa_text(gpa) if gpa else None, "current": bool(found and found["current"])}
            out.append(current)
            continue
        if institution and current and not current["institution"]:
            current["institution"] = institution
            if current["year"] is None:
                current["year"] = years[-1] if years else None
        elif institution:
            current = {"degree": "", "institution": institution, "year": years[-1] if years else None, "gpa": None, "current": False}
            out.append(current)
        if current and gpa and not current["gpa"]:
            current["gpa"] = _gpa_text(gpa)
        if current and found and not institution:
            current["current"] = found["current"]
            current["year"] = None if found["current"] else (_range_year(found) or current["year"])
        elif current and not found and not institution and not bullet and years and not current["year"]:
            current["year"] = years[-1]
    return [item for item in out if item["degree"] or item["institution"]][:5]


def format_education(item: dict) -> str:
    return " · ".join(p for p in [
        item.get("degree"), item.get("institution"),
        "حتى الآن" if item.get("current") else (ar_digits(item["year"]) if item.get("year") else ""),
        f"المعدل {item['gpa']}" if item.get("gpa") else "",
    ] if p)
