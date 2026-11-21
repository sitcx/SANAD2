"""Splits a CV into its standard sections (Arabic and English headings), the way an ATS parses it."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from src.agent.text.arabic import normalize_arabic


@dataclass
class Section:
    kind: str          # summary | experience | volunteer | education | skills | certifications | languages | projects | awards | contact | other | header
    heading: str
    lines: list[str] = field(default_factory=list)


# Written in normalised form (ة->ه، أ/إ->ا، ى->ي) because they are tested on normalize_arabic(line).
_HEADINGS = [
    ("experience", r"^(ال)?(خبرات|خبره)( ال(عمليه|مهنيه|وظيفيه|سابقه|العمليه))?$|^(السجل المهني|المسيره المهنيه|التاريخ الوظيفي|الوظائف السابقه|الخبرات والوظائف|التدريب التعاوني|التدريب الميداني|الخبرات والتدريب)$|^((work|professional|relevant|practical|internship|training) )?experiences?$|^(employment|work|career|job) history$|^(internships?|co-?op training|cooperative training|practical training)$"),
    ("volunteer", r"^(ال)?(اعمال )?(تطوع|تطوعيه|العمل التطوعي|الاعمال التطوعيه|الانشطه|الانشطه والتطوع|التطوع والانشطه)$|^(volunteer(ing)?( work| experience| activities)?|(extracurricular|student|leadership) activities|activities|volunteering (and|&) activities)$"),
    ("education", r"^(ال)?(تعليم|مؤهلات|مؤهل)( ال(علميه|علمي|اكاديميه|دراسيه))?$|^(الدراسه|التحصيل العلمي|المؤهلات العلميه|المؤهل العلمي)$|^(education( (and|&) training)?|academic background|academic qualifications|qualifications|educational background)$"),
    ("skills", r"^(ال)?مهارات( ال(تقنيه|فنيه|شخصيه|مهنيه|اساسيه|حاسوبيه|اداريه))?$|^(القدرات|الكفاءات|الادوات والبرامج|البرامج|المهارات والادوات)$|^((technical|core|key|soft|hard|professional|computer|it) )?skills( (and|&) (tools|abilities|competencies|technologies))?( summary)?$|^(core )?competencies$|^(tools|technologies|tech stack|expertise|tools (and|&) technologies)$"),
    ("certifications", r"^(ال)?(شهادات|رخص|دورات|الدورات التدريبيه|البرامج التدريبيه|التدريب|الشهادات والدورات|الدورات والشهادات|الشهادات والدورات التدريبيه)( المهنيه| الاحترافيه)?$|^(certifications?|certificates?|licenses?( (and|&) certifications)?|courses|training|professional development|(certifications?|certificates?) (and|&) (courses|training)|(courses|training) (and|&) (certifications?|certificates?)|licenses (and|&) certificates)$"),
    ("languages", r"^(ال)?لغات$|^languages?$"),
    ("summary", r"^(ال)?(ملخص|نبذه|الهدف|هدف)( ال(مهني|وظيفي|شخصي))?( عني| مختصره)?$|^(عني|نبذه عني|التعريف)$|^((professional |career |executive )?summary|profile|professional profile|objective|career objective|about( me)?)$"),
    ("projects", r"^(ال)?مشاريع( ال(عمليه|اكاديميه|شخصيه))?$|^(مشروع التخرج|المشاريع والابحاث)$|^((academic|personal|key|selected|graduation|university) )?projects?$"),
    ("awards", r"^(ال)?(جوائز|انجازات|الجوائز والانجازات|التكريم)$|^(awards?|achievements|honou?rs( (and|&) awards)?|awards (and|&) (achievements|honou?rs))$"),
    ("contact", r"^(ال)?(معلومات|بيانات)( ال)?(شخصيه|التواصل|الاتصال)$|^(contact( info| information| details)?|personal (info|information|details))$"),
    ("other", r"^(ال)?(هوايات|اهتمامات|المعرفون|مراجع)$|^(hobbies|interests|references|publications|memberships)$"),
]
_COMPILED = [(kind, re.compile(pattern)) for kind, pattern in _HEADINGS]


def heading_kind(line: str) -> str | None:
    key = normalize_arabic(re.sub(r"^\d+[.)]\s*", "", line.replace("&", " and ")))
    key = re.sub(r"\s+", " ", re.sub(r"\s*[:：]\s*$", "", key)).strip()
    if not key or len(key) > 50:
        return None
    return next((kind for kind, pattern in _COMPILED if pattern.search(key)), None)


def cv_lines(text: str) -> list[str]:
    """Lines with whitespace collapsed and typographic apostrophes made plain."""
    out = []
    for line in re.split(r"\r?\n", text):
        line = re.sub(r"\s+", " ", re.sub(r"\|{3,}", " ", re.sub("[ʼ’‘]", "'", line))).strip()
        if line:
            out.append(line)
    return out


def _unknown_heading(line: str) -> bool:
    """«REFERENCES:» — all capitals and a colon. It closes the previous section."""
    return bool(re.fullmatch(r"[A-Z][A-Z &/-]{3,40}\s*:", line))


def split_sections(text: str) -> list[Section]:
    sections = [Section("header", "")]
    resume: Section | None = None   # after a one-line heading («Languages: Arabic»), go back to the section we were in
    for line in cv_lines(text):
        kind = heading_kind(line)
        if kind:
            sections.append(Section(kind, line))
            resume = None
            continue
        inline = re.match(r"^([^:：]{2,45})[:：]\s*(.+)$", line)
        inline_kind = heading_kind(inline.group(1)) if inline else None
        if inline and inline_kind:
            previous = sections[-1]
            sections.append(Section(inline_kind, inline.group(1).strip(), [inline.group(2).strip()]))
            resume = previous if previous.kind != inline_kind else resume
            continue
        if len(sections) > 1 and _unknown_heading(line):
            sections.append(Section("other", line))
            resume = None
            continue
        if resume:
            sections.append(Section(resume.kind, resume.heading))
            resume = None
        sections[-1].lines.append(line)
    return [s for s in sections if s.lines or s.kind != "header"]


def lines_of(sections: list[Section], *kinds: str) -> list[str]:
    return [line for s in sections if s.kind in kinds for line in s.lines]
