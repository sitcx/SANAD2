from __future__ import annotations

from src.agent.job_agent.graph import recommend_jobs
from src.agent.job_agent.tools.read_cv import missing_fields, read_cv
from src.agent.job_agent.tools.score_job import score_job
from src.agent.job_agent.tools.search_jobs import load_jobs, search_jobs

ARABIC_CV = """الاسم: سارة
المدينة: الرياض
تخصص: نظم المعلومات
خبرة 2 سنوات في تحليل البيانات باستخدام Excel و SQL، والتواصل الكتابي مع العملاء.
"""


def test_read_cv_rules_arabic(tmp_path):
    cv = tmp_path / "cv.txt"
    cv.write_text(ARABIC_CV, encoding="utf-8")
    profile = read_cv(str(cv))
    assert {"excel", "sql", "data analysis", "written communication"} <= set(profile["skills"])
    assert profile["city"] == "riyadh"
    assert profile["experience_years"] == 2.0
    assert missing_fields(profile) == []


def test_read_cv_docx(tmp_path):
    import zipfile

    ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    paragraphs = "".join(f"<w:p><w:r><w:t>{line}</w:t></w:r></w:p>" for line in ARABIC_CV.strip().splitlines())
    cv = tmp_path / "cv.docx"
    with zipfile.ZipFile(cv, "w") as docx:
        docx.writestr("word/document.xml", f'<w:document xmlns:w="{ns}"><w:body>{paragraphs}</w:body></w:document>')
    profile = read_cv(str(cv))
    assert profile["city"] == "riyadh" and "sql" in profile["skills"]


def test_missing_info_then_answers(tmp_path):
    cv = tmp_path / "cv.txt"
    cv.write_text("Skills: Figma, design", encoding="utf-8")
    first = recommend_jobs(cv_file=str(cv))
    assert first["missing_info"] == ["city"]
    assert "recommended" not in first

    second = recommend_jobs(cv_file=str(cv), answers={"city": "جدة"})
    assert second["missing_info"] == []
    assert second["recommended"][0]["job_id"] == "designer"


def test_search_widens_and_ranks():
    profile = {"skills": ["Excel", "SQL"], "city": "Riyadh", "experience_years": 3}
    assert [j["id"] for j in search_jobs(profile)] == ["analyst"]
    state = recommend_jobs(profile=profile)
    assert state["widened"] is True                       # 1 match < min_matches (3)
    matches = [j["match"] for j in state["jobs"]]
    assert matches == sorted(matches, reverse=True)
    top = state["recommended"][0]
    assert top["job_id"] == "analyst" and top["match"] >= 70   # 2 of 3 skills + city + experience
    assert top["title"] == "Data Analyst" and top["reason"]
    assert len(state["recommended"]) <= 3


def test_score_job_arabic_skills_match_english_job():
    analyst = next(j for j in load_jobs() if j["id"] == "analyst")
    result = score_job({"skills": ["تحليل البيانات", "اكسل"], "city": "الرياض"}, analyst)
    assert set(result["matched_skills"]) == {"Excel", "Data analysis"}
    assert 0 <= result["match"] <= 100
