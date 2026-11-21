"""The teammate's CV-reading and matching tests (backend-cv-reading / backend-cv-diverse), ported to pytest.

Same CVs (made-up people) and the same expected results as the TypeScript version, so the Python port
reads every CV exactly like the original.
"""
from __future__ import annotations

from datetime import datetime, timezone

from src.agent.job_agent.ats.experience import duration_ar, find_date_range, format_experience, parse_experience, total_years
from src.agent.job_agent.ats.matching import match_job, skills_match
from src.agent.job_agent.ats.reader import heuristic_profile, merge_profiles, supported_by_text, verified_claude_profile
from src.agent.job_agent.ats.sections import split_sections
from src.agent.job_agent.ats.skills import canonical_skill, find_skills
from src.agent.text.arabic import arabic_variants, normalize_arabic
from src.database.candidate_db import fingerprint_of

NOW = datetime(2026, 11, 18, 9, tzinfo=timezone.utc)

ENGLISH_CV = """KHALID AL-HARBI
Riyadh, Saudi Arabia · khalid@example.com
PROFESSIONAL SUMMARY
Customer service specialist with strong written communication and CRM experience.
WORK EXPERIENCE
Customer Support Specialist
STC Solutions | Riyadh
Mar 2023 – Present
• Resolved 60+ chat and email tickets daily using Zendesk with 95% satisfaction.
• Trained 4 new agents on written support guidelines.
Call Center Agent (chat)
Jarir Bookstore, Jeddah
06/2021 - 02/2023
- Handled online orders and returns through live chat.
EDUCATION
Diploma in Business Administration – Riyadh College of Technology – 2020
SKILLS
Zendesk • Salesforce • MS Office (Advanced) • Typing 60 WPM • Problem solving
LANGUAGES
Arabic (Native), English (Fluent)"""

NURSE_CV = """أمل الشهري — ممرضة
خبرة في مستشفى الملك فهد التخصصي بالدمام من 1440هـ إلى 1445هـ في رعاية المرضى وتسجيل السجلات الطبية.
متدربة تمريض في مستشفى الحرس الوطني 2018 - 2019
دبلوم التمريض، كلية الأمير سلطان للعلوم الصحية 2018
BLS, ACLS, مكافحة العدوى، رعاية المرضى"""

IT_CV = """Lama Saleh Alqahtani
lama.saleh@example.com | +966 55 000 1122 | Jeddah, Saudi Arabia | linkedin.com/in/lama-example
SUMMARY :
Software engineer with experience building web and mobile applications for e-commerce and logistics companies in Saudi Arabia.
PROFESSIONAL EXPERIENCE :
Software Engineer - Salla, Jeddah
•Built 12 REST APIs with Node.js and PostgreSQL serving 40,000 daily orders.
•Reduced page load time by 35% by moving the storefront to React and Next.js.
Mar 2023 – Present
Saudi Arabia, Jeddah
•Mentored 3 junior developers and reviewed code on GitHub.
Junior Web Developer – Tamara
•Developed checkout screens in React and TypeScript.
Jan 2022 – Feb 2023
Riyadh, Saudi Arabia
EDUCATION :
Bachelor of Science in Computer Science, King Abdulaziz University
Sep 2017 – Jun 2021
PROJECTS :
Delivery Tracker App, Flutter, Firebase, Google Maps API
Built a mobile app that shows live delivery status to customers.
VOLUNTEER EXPERIENCE :
Workshop Mentor, Google Developer Group Jeddah
Taught web basics to 50 high-school students.
Feb 2022 – Dec 2022
SKILLS :
Technical Skills: JavaScript, TypeScript, React, Node.js, PostgreSQL, Docker, Git
Soft Skills: Teamwork | Problem Solving | Time Management
LANGUAGES :
Arabic (Native), English (Fluent)"""

HR_CV = """عبدالله فهد المطيري
البريد: abdullah@example.com | الجوال: 0501234567 | الرياض
الملخص المهني
أخصائي موارد بشرية وإدارة أعمال بخبرة في التوظيف وإدارة شؤون الموظفين وإعداد التقارير الإدارية للإدارة العليا.
الخبرات العملية
أخصائي موارد بشرية - شركة المراعي - الرياض - 2021 - الآن
• أدرت إجراءات توظيف 120 موظفًا سنويًا باستخدام نظام SAP.
• أعددت تقارير شهرية للإدارة العليا عن الحضور والرواتب.
منسق إداري - بنك الرياض - 2018 - 2021
• نظمت المراسلات الإدارية وأرشفة العقود.
التعليم
بكالوريوس إدارة أعمال - جامعة الملك سعود - 2018 - المعدل 4.2 من 5
الدورات والشهادات
• شهادة SHRM-CP - جمعية إدارة الموارد البشرية 2022
• إدارة المشاريع الاحترافية PMP - معهد إدارة المشاريع
المهارات
الموارد البشرية، التوظيف، SAP، Excel، إعداد التقارير، التفاوض، القيادة
اللغات
العربية: اللغة الأم، الإنجليزية: جيد جدًا"""

ENGINEER_CV = """Omar Khalid Alzahrani
Mechanical Engineer
Jubail, Saudi Arabia | omar.eng@example.com | +966 50 111 2233
Professional Summary
Mechanical engineer with experience in plant maintenance, reliability and HVAC design for petrochemical plants.
Work Experience
Senior Mechanical Engineer | SABIC | Jubail | Jan 2022 – Present
- Led preventive maintenance for 40 rotating equipment units, cutting downtime by 18%.
- Designed HVAC upgrades in AutoCAD and Revit.
Mechanical Engineer | Saudi Aramco | Dhahran | Jul 2019 – Dec 2021
- Performed root cause analysis on pump failures.
Engineering Intern | Marafiq | Jubail | Jun 2018 – Aug 2018
- Assisted the reliability team with vibration analysis.
Education
B.Sc. Mechanical Engineering – King Fahd University of Petroleum and Minerals – 2019
Certifications
PMP – Project Management Institute – 2023
Skills
AutoCAD, Revit, SolidWorks, HVAC, Preventive Maintenance, Root Cause Analysis, MS Project
Languages
Arabic, English"""

GRADUATE_CV = """ريم سعد الدوسري
الدمام | reem@example.com | 0555555555
الهدف الوظيفي
خريجة محاسبة أبحث عن فرصة في المحاسبة المالية أو المراجعة لدى جهة تهتم بالتطوير المهني.
التعليم
بكالوريوس المحاسبة، جامعة الإمام عبدالرحمن بن فيصل، 2025، المعدل 4.6 من 5
التدريب
متدربة محاسبة - شركة أرامكو السعودية - يونيو 2024 - أغسطس 2024
• أدخلت 300 قيد يومية في نظام SAP وطابقت كشوفات البنوك.
المشاريع
مشروع التخرج: تحليل القوائم المالية لشركات السوق السعودي، Excel، Power BI
الأعمال التطوعية
متطوعة - جمعية إنسان - 2022 - 2023
• نظمت حملات توزيع للأسر المحتاجة.
المهارات
المحاسبة المالية، Excel، SAP، الزكاة والضريبة، العمل الجماعي"""

CAREER_CV = """NOURA ABDULLAH
Customer Experience Manager
Riyadh · noura@example.com · +966 54 999 8877
EXPERIENCE
2022 – Present
Customer Experience Manager
stc, Riyadh
• Led a team of 25 chat agents and raised CSAT from 78% to 91%.
2019 – 2022
Team Leader, Customer Care
Almarai, Riyadh
• Built Zendesk workflows that cut response time by 40%.
2017 – 2019
Customer Service Representative
Jarir Bookstore, Riyadh
• Handled 80+ online inquiries per day.
2016 – 2017
Sales Associate
eXtra, Riyadh
EDUCATION
Bachelor of Business Administration, Prince Sultan University, 2016
SKILLS
Zendesk, Salesforce, CRM, Customer Experience, Team Leadership, Written Communication"""


def kinds(profile: dict) -> list[str]:
    return [role["kind"] for role in profile["experienceDetails"]]


# ---------------------------------------------------------------- reading experience like a recruiter

def test_date_ranges_in_arabic_english_numeric_and_hijri():
    assert {k: find_date_range("محلل بيانات - 2022 - الآن")[k] for k in ("start", "current")} == {"start": "2022", "current": True}
    assert {k: find_date_range("Mar 2023 – Present")[k] for k in ("start", "current")} == {"start": "2023-03", "current": True}
    assert {k: find_date_range("06/2021 - 02/2023")[k] for k in ("start", "end", "current")} == {"start": "2021-06", "end": "2023-02", "current": False}
    assert {k: find_date_range("من يناير ٢٠٢٠ إلى مارس ٢٠٢١")[k] for k in ("start", "end")} == {"start": "2020-01", "end": "2021-03"}
    assert {k: find_date_range("من 1440هـ إلى 1445هـ")[k] for k in ("start", "end")} == {"start": "2019", "end": "2024"}
    assert {k: find_date_range("منذ 2019")[k] for k in ("start", "current")} == {"start": "2019", "current": True}


def test_durations_in_natural_arabic():
    assert [duration_ar(m) for m in (1, 14, 24, 45, 144)] == ["شهر", "سنة وشهران", "سنتان", "٣ سنوات و٩ أشهر", "١٢ سنة"]


def test_multi_line_english_roles():
    profile = heuristic_profile(ENGLISH_CV, NOW)
    assert profile["experience"] == ["Customer Support Specialist · STC Solutions · ٣ سنوات و٩ أشهر", "Call Center Agent (chat) · Jarir Bookstore · سنة و٩ أشهر"]
    first = profile["experienceDetails"][0]
    assert (first["title"], first["organization"], first["location"], first["current"], first["duration"]) == \
        ("Customer Support Specialist", "STC Solutions", "Riyadh", True, "٣ سنوات و٩ أشهر")
    assert len(first["highlights"]) == 2
    assert profile["yearsExperience"] == 5.5
    assert profile["careerLevel"] == "متوسط الخبرة"


def test_own_tool_names_arabic_concepts_and_no_skill_from_the_degree():
    profile = heuristic_profile(ENGLISH_CV, NOW)
    assert {"Zendesk", "Salesforce", "MS Office", "حل المشكلات"} <= set(profile["skills"])
    assert "الأعمال الإدارية" not in profile["skills"]
    assert "Problem solving" not in profile["skills"]
    assert profile["languages"] == ["العربية", "الإنجليزية"]
    assert profile["education"] == ["Diploma in Business Administration · Riyadh College of Technology · ٢٠٢٠"]


def test_unstructured_healthcare_cv_with_hijri_dates():
    profile = heuristic_profile(NURSE_CV, NOW)
    assert profile["experience"] == ["ممرضة · مستشفى الملك فهد التخصصي بالدمام · ٥ سنوات", "متدربة تمريض · مستشفى الحرس الوطني · سنة"]
    assert profile["summary"].startswith("ممرضة بخبرة ٦ سنوات، آخرها لدى مستشفى الملك فهد التخصصي بالدمام.")
    assert {"رعاية المرضى", "الإسعافات الأولية والإنعاش", "مكافحة العدوى"} <= set(profile["skills"])
    assert profile["suggestedRoles"][0] == "ممرضة"


def test_overlapping_roles_are_not_double_counted():
    roles = parse_experience(["مطور - شركة أ - 01/2020 - 12/2021", "مستشار - شركة ب - 06/2021 - 12/2022"])
    assert total_years(roles, NOW) == 3
    assert format_experience(roles[0], NOW) == "مطور · شركة أ · سنتان"


def test_section_headings_in_both_languages():
    text = "الخبرات العملية\nx\nEDUCATION\ny\nالمهارات: Excel، SQL\nLanguages:\nArabic"
    assert [s.kind for s in split_sections(text)] == ["experience", "education", "skills", "languages"]


# ---------------------------------------------------------------- verifying Claude's reading

CV = "محلل بيانات - شركة المراعي - 2022 - الآن: بناء لوحات Power BI وتنظيف البيانات باستخدام SQL."
AI = {
    "summary": "محلل بيانات يبني لوحات معلومات.",
    "experience": [
        {"title": "محلل بيانات", "organization": "شركة المراعي", "location": "", "kind": "job", "start": "2022", "end": "present",
         "highlights": ["بنى لوحات Power BI."], "evidence": "محلل بيانات - شركة المراعي"},
        {"title": "مدير مشاريع", "organization": "شركة نيوم", "location": "", "kind": "job", "start": "2019", "end": "2021",
         "highlights": [], "evidence": "مدير مشاريع في نيوم"},
    ],
    "skills": [{"name": "Power BI", "kind": "tool", "evidence": "لوحات Power BI"}, {"name": "SQL", "kind": "technical", "evidence": "باستخدام SQL"},
               {"name": "Tableau", "kind": "tool", "evidence": "Tableau dashboards"}],
    "education": [], "certifications": [], "languages": ["العربية"], "suggestedRoles": ["محلل بيانات"], "searchKeywords": ["Data Analyst"],
    "projects": [{"name": "لوحات Power BI", "tools": ["Power BI"], "description": "لوحة مبيعات."}, {"name": "تطبيق نيوم الذكي", "tools": ["Flutter"], "description": ""}],
}


def test_quotes_match_despite_spelling_variants():
    assert supported_by_text("شركه المراعى", "محلل بيانات شركه المراعي")


def test_drops_unsupported_roles_and_skills_and_computes_duration():
    profile = verified_claude_profile(AI, CV, NOW)
    assert [r["title"] for r in profile["experienceDetails"]] == ["محلل بيانات"]
    assert profile["experience"][0] == "محلل بيانات · شركة المراعي · ٤ سنوات"
    detail = profile["experienceDetails"][0]
    assert (detail["period"], detail["kind"], detail["highlights"]) == ("٢٠٢٢ – الآن", "job", ["بنى لوحات Power BI"])
    assert [p["name"] for p in profile["projects"]] == ["لوحات Power BI"]
    assert profile["skills"] == ["SQL", "Power BI"]
    assert profile["engine"] == "claude"


def test_offline_reader_fills_gaps_without_duplicates():
    merged = merge_profiles(verified_claude_profile(AI, CV, NOW), heuristic_profile(CV, NOW))
    assert merged["skills"].count("SQL") == 1
    assert "Data Analyst" in merged["searchKeywords"]


def test_skills_outside_the_taxonomy_match_by_shared_words():
    assert skills_match("إدارة المشاريع الإنشائية", "إدارة المشاريع")
    assert skills_match("Zendesk", "CRM")
    assert skills_match("اكسل", "Microsoft Excel")
    assert not skills_match("Figma", "SQL")


# ---------------------------------------------------------------- ATS reading across different CVs

def test_it_two_column_layout_roles_volunteering_projects():
    profile = heuristic_profile(IT_CV, NOW, file_name="cv.pdf")
    assert profile["experience"] == ["Software Engineer · Salla · ٣ سنوات و٩ أشهر", "Junior Web Developer · Tamara · سنة وشهران",
                                     "Workshop Mentor · Google Developer Group Jeddah · ١١ شهرًا · تطوعي"]
    assert kinds(profile) == ["job", "job", "volunteer"]
    first, second = profile["experienceDetails"][:2]
    assert (first["location"], first["current"], first["period"]) == ("Jeddah", True, "مارس ٢٠٢٣ – الآن")
    assert second["location"] == "Riyadh, Saudi Arabia"
    assert profile["yearsExperience"] == 4.9
    assert profile["jobTitles"] == ["Software Engineer", "Junior Web Developer"]
    assert len(profile["projects"]) == 1 and profile["projects"][0]["name"] == "Delivery Tracker App"
    assert profile["projects"][0]["tools"] == ["Flutter", "Firebase", "Google Maps API"]
    assert "Delivery Tracker" not in " ".join(profile["experience"])
    assert {"JavaScript", "React", "Node.js", "Docker", "Git", "Flutter", "Firebase", "العمل الجماعي"} <= set(profile["skills"])
    assert profile["education"] == ["Bachelor of Science in Computer Science · King Abdulaziz University · ٢٠٢١"]
    assert profile["languages"] == ["العربية", "الإنجليزية"]
    assert {"Software Engineer", "مطور برمجيات"} <= set(profile["suggestedRoles"])
    contact = profile["ats"]["contact"]
    assert (contact["email"], contact["phone"], contact["city"], contact["linkedin"]) == (True, True, "Jeddah", True)
    assert profile["ats"]["score"] >= 85


def test_hr_arabic_one_line_roles_certificates_gpa():
    profile = heuristic_profile(HR_CV, NOW)
    assert profile["experience"] == ["أخصائي موارد بشرية · شركة المراعي · ٥ سنوات", "منسق إداري · بنك الرياض · ٣ سنوات"]
    assert profile["yearsExperience"] == 8
    assert profile["careerLevel"] == "خبير"
    assert profile["education"] == ["بكالوريوس إدارة أعمال · جامعة الملك سعود · ٢٠١٨ · المعدل 4.2/5"]
    assert profile["certifications"] == ["شهادة SHRM-CP · جمعية إدارة الموارد البشرية · ٢٠٢٢", "إدارة المشاريع الاحترافية PMP · معهد إدارة المشاريع"]
    assert {"الموارد البشرية", "SAP", "Excel", "إعداد التقارير", "التفاوض", "القيادة"} <= set(profile["skills"])
    assert profile["suggestedRoles"][0] == "أخصائي موارد بشرية"
    assert "محاسب" not in profile["suggestedRoles"]
    assert profile["ats"]["contact"]["city"] == "الرياض"


def test_engineering_pipe_layout_internship_and_tool_names():
    profile = heuristic_profile(ENGINEER_CV, NOW)
    assert profile["experience"] == ["Senior Mechanical Engineer · SABIC · ٤ سنوات و١١ شهرًا", "Mechanical Engineer · Saudi Aramco · سنتان و٦ أشهر",
                                     "Engineering Intern · Marafiq · ٣ أشهر"]
    assert kinds(profile) == ["job", "job", "internship"]
    assert [r["location"] for r in profile["experienceDetails"]] == ["Jubail", "Dhahran", "Jubail"]
    assert profile["yearsExperience"] == 7.7
    assert {"AutoCAD", "Revit", "SolidWorks", "HVAC", "MS Project"} <= set(profile["skills"])
    assert profile["education"] == ["B.Sc. Mechanical Engineering · King Fahd University of Petroleum and Minerals · ٢٠١٩"]
    assert profile["certifications"] == ["PMP · Project Management Institute · ٢٠٢٣"]
    assert profile["suggestedRoles"][0] == "Senior Mechanical Engineer"


def test_new_graduate_internship_project_and_volunteering_are_not_jobs():
    profile = heuristic_profile(GRADUATE_CV, NOW)
    assert profile["experience"] == ["متدربة محاسبة · شركة أرامكو السعودية · ٣ أشهر", "متطوعة · جمعية إنسان · سنة · تطوعي"]
    assert kinds(profile) == ["internship", "volunteer"]
    assert profile["jobTitles"] == ["متدربة محاسبة"]
    assert profile["careerLevel"] == "حديث تخرج (تدريب تعاوني)"
    assert profile["certifications"] == []
    assert len(profile["projects"]) == 1
    assert profile["projects"][0]["name"] == "تحليل القوائم المالية لشركات السوق السعودي"
    assert profile["projects"][0]["tools"] == ["Excel", "Power BI"]
    assert profile["education"] == ["بكالوريوس المحاسبة · جامعة الإمام عبدالرحمن بن فيصل · ٢٠٢٥ · المعدل 4.6/5"]
    assert {"محاسبة", "محاسب"} <= set(profile["suggestedRoles"])


def test_long_career_date_first_with_lower_case_company():
    profile = heuristic_profile(CAREER_CV, NOW)
    assert profile["experience"] == ["Customer Experience Manager · stc · ٤ سنوات", "Team Leader، Customer Care · Almarai · ٣ سنوات",
                                     "Customer Service Representative · Jarir Bookstore · سنتان", "Sales Associate · eXtra · سنة"]
    assert profile["yearsExperience"] == 10
    assert profile["careerLevel"] == "خبير أول"
    assert {"Zendesk", "Salesforce", "CRM", "التواصل الكتابي", "القيادة"} <= set(profile["skills"])


# ---------------------------------------------------------------- matching compares real requirements

FRONTEND = {"title": "مطور واجهات أمامية", "english": "Frontend Developer", "description": "تطوير واجهات بـ React وTypeScript وJavaScript.",
            "skills": ["React", "TypeScript", "JavaScript"], "location": "جدة", "mode": "هجين"}
MECHANICAL = {"title": "مهندس ميكانيكي", "english": "Mechanical Engineer", "description": "صيانة المعدات وتصميم أنظمة التكييف. خبرة 5 سنوات وبكالوريوس هندسة.",
              "skills": ["AutoCAD", "HVAC", "الصيانة"], "location": "الجبيل", "mode": "حضوري"}
COBOL = {"title": "Software Engineer", "english": "Software Engineer", "description": "Maintain banking systems in COBOL on IBM mainframes.",
         "skills": ["COBOL", "Mainframe"], "location": "الرياض", "mode": "حضوري"}


def test_each_cv_scored_against_each_job_from_the_requirements():
    it_profile, hr, engineer = heuristic_profile(IT_CV, NOW), heuristic_profile(HR_CV, NOW), heuristic_profile(ENGINEER_CV, NOW)
    it_frontend = match_job(it_profile, FRONTEND, IT_CV)
    assert it_frontend["score"] >= 85 and it_frontend["missingSkills"] == []
    assert match_job(hr, FRONTEND, HR_CV)["score"] < 25
    engineer_match = match_job(engineer, MECHANICAL, ENGINEER_CV)
    assert engineer_match["score"] >= 80 and "AutoCAD" in engineer_match["reason"]
    assert match_job(it_profile, MECHANICAL, IT_CV)["score"] < 25


def test_names_the_gaps_and_a_same_title_job_stays_low():
    it_profile = heuristic_profile(IT_CV, NOW)
    result = match_job(it_profile, COBOL, IT_CV)
    assert "Software Engineer" in it_profile["jobTitles"]
    assert result["score"] < 30
    assert result["missingSkills"] == ["COBOL", "Mainframe"]
    assert "COBOL" in result["reason"]


# ---------------------------------------------------------------- backend-agents.test.ts (teammate), ported

NOURA_CV = """نورة العتيبي
محللة بيانات بخبرة 3 سنوات في تحليل المبيعات وإعداد التقارير.
الخبرات العملية
محلل بيانات - شركة المراعي - 2022 - الآن: تنظيف بيانات المبيعات باستخدام Excel و SQL وبناء لوحات Power BI.
أخصائي إدخال بيانات - بنك الرياض - 2021 - 2022: إدخال البيانات والأرشفة.
التعليم
بكالوريوس نظم المعلومات - جامعة الملك سعود - 2021
اللغات: العربية، الإنجليزية، لغة الإشارة السعودية"""

ANALYST = {"title": "محلل بيانات", "english": "Data Analyst", "description": "حوّل البيانات إلى رؤى واضحة تساعد الفريق على اتخاذ قرارات أفضل.",
           "skills": ["Excel", "SQL", "تحليل البيانات"], "location": "الرياض", "mode": "هجين"}
DESIGNER = {"title": "مصمم تجربة وواجهة مستخدم", "english": "UI/UX Designer", "description": "صمّم تجارب رقمية سهلة الاستخدام تجعل المنتجات أكثر وضوحًا للجميع.",
            "skills": ["Figma", "بحث المستخدم", "التصميم"], "location": "جدة", "mode": "هجين"}


def test_arabic_text_helpers_fold_variants_diacritics_and_digits():
    assert normalize_arabic("إدارةُ المشاريعِ ٢٠٢٤") == "اداره المشاريع 2024"
    assert "بيانات" in arabic_variants("والبيانات")


def test_offline_cv_agent_without_false_positives():
    profile = heuristic_profile(NOURA_CV, NOW)
    assert {"Excel", "SQL", "Power BI", "تحليل البيانات", "إعداد التقارير"} <= set(profile["skills"])
    assert "التعليم والتدريب" not in profile["skills"] and "البيع والمبيعات" not in profile["skills"]   # headings / «تحليل المبيعات» are not skills
    assert profile["experience"] == ["محلل بيانات · شركة المراعي · ٤ سنوات", "أخصائي إدخال بيانات · بنك الرياض · سنة"]
    assert "بكالوريوس" in profile["education"][0]
    assert "لغة الإشارة السعودية" in profile["languages"]
    assert profile["yearsExperience"] == 5                      # computed from the dates, not copied from «3 سنوات»


def test_skill_spellings_map_to_one_canonical_name():
    assert canonical_skill("اكسل") == "Excel" and canonical_skill("Microsoft Excel") == "Excel"
    assert {"خدمة العملاء", "CRM"} <= set(find_skills("خبرة في خدمة العملاء وZendesk"))


def test_data_job_ranks_above_design_with_an_arabic_reason():
    profile = heuristic_profile(NOURA_CV, NOW)
    good, weak = match_job(profile, ANALYST), match_job(profile, DESIGNER)
    assert good["score"] > 90 and weak["score"] < 40
    assert "Excel" in good["reason"] and {"Excel", "SQL"} <= set(good["matchedSkills"])


def test_the_same_posting_gets_the_same_fingerprint():
    a = fingerprint_of("مُدخِل بيانات", "شركة أ", "https://example.com/jobs/1?ref=x")
    b = fingerprint_of("مدخل بيانات", "شركه ا", "https://EXAMPLE.com/jobs/1")
    assert a == b
