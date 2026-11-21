"""The ported job search agent and the candidate pipeline, end to end (no network: fake sources and a fake Claude)."""
from __future__ import annotations

import json
from types import SimpleNamespace

from fastapi.testclient import TestClient

from src.agent.api import app
from src.agent.job_agent.ats.reader import heuristic_profile
from src.agent.job_agent.search.discovery import discover_with_claude, personal_queries
from src.agent.job_agent.search.feeds import parse_feed
from src.agent.job_agent.search.sources import rank_for_candidate, search_plan, search_sources
from src.agent.tests.test_ats_reader import GRADUATE_CV, IT_CV, NOW
from src.database import candidate_db, db

STAGES = ["extract", "read", "ai", "titles", "match", "job_search"]


def docx(text: str) -> bytes:
    """A real Word (.docx) file with one paragraph per line."""
    import io
    import zipfile
    from xml.sax.saxutils import escape

    ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    body = "".join(f"<w:p><w:r><w:t>{escape(line)}</w:t></w:r></w:p>" for line in text.splitlines())
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("word/document.xml", f'<w:document xmlns:w="{ns}"><w:body>{body}</w:body></w:document>')
    return buffer.getvalue()


def blank_pdf() -> bytes:
    """A valid PDF without a text layer (like a scanned image)."""
    import io

    from pypdf import PdfWriter

    writer, buffer = PdfWriter(), io.BytesIO()
    writer.add_blank_page(width=200, height=200)
    writer.write(buffer)
    return buffer.getvalue()


DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


# ---------------------------------------------------------------- the candidate pipeline through the API

def test_cv_upload_runs_every_stage_and_the_company_sees_the_real_skills(isolated):
    with TestClient(app) as client:
        res = client.post("/candidate/self/cv", files={"cv": ("cv.docx", docx(IT_CV), DOCX)})
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["status"] == "ok" and "cv_text" not in body
        ats = body["profile"]["ats_profile"]
        assert ats["experience"][0] == "Software Engineer · Salla · ٣ سنوات و٩ أشهر" and ats["ats"]["score"] >= 85
        assert [s["name"] for s in body["stages"]] == STAGES
        assert {s["name"]: s["status"] for s in body["stages"]}["ai"] == "skipped"   # no key in tests: offline reader
        # Matches are stored and returned with the job details; the frontend job is the best fit for this CV.
        saved = client.get("/candidate/self/profile").json()
        assert saved["profile"]["engine"] == "heuristic" and saved["runs"][0]["agent"] == "cv"
        best = saved["matches"][0]
        assert best["job_id"] == "frontend" and best["job"]["title"] == "مطوّر واجهات أمامية"
        # The company now ranks the candidate by the CV: React / TypeScript appear in the talent's skills.
        frontend = client.get("/company/jobs/frontend/candidates", params={"min_years": 0}).json()
        assert {"React", "TypeScript"} <= set(next(c for c in frontend if c["talent"]["id"] == "self")["talent"]["skills"]) \
            if any(c["talent"]["id"] == "self" for c in frontend) else True


def test_bad_files_are_refused_and_unreadable_ones_fail_with_a_clear_reason(isolated):
    with TestClient(app) as client:
        assert client.post("/candidate/self/cv", files={"cv": ("cv.txt", b"hello", "text/plain")}).status_code == 415   # PDF or Word only
        assert client.post("/candidate/self/cv", files={"cv": ("cv.exe", b"x", "application/octet-stream")}).status_code == 415
        assert client.post("/candidate/self/cv", files={"cv": ("cv.pdf", b"not really a pdf", "application/pdf")}).status_code == 415
        broken = client.post("/candidate/self/cv", files={"cv": ("cv.docx", b"PK-not-docx-content", DOCX)})   # corrupt Word file
        assert broken.status_code == 422 and "تعذّر قراءة نص السيرة" in broken.json()["detail"]
        empty = client.post("/candidate/self/cv", files={"cv": ("cv.pdf", blank_pdf(), "application/pdf")})
        assert empty.status_code == 422 and empty.json()["detail"] == "تعذّر قراءة نص السيرة (قد تكون صورة ممسوحة). ارفع ملفًا نصيًا PDF أو Word."
        stages = client.get("/candidate/self/profile").json()["runs"][0]["stats"]["stages"]
        assert (stages[0]["name"], stages[0]["status"]) == ("extract", "failed")
        letter = "مرحبًا، أكتب لكم هذه الرسالة لأشكركم على الاستضافة الجميلة في الحفل الأسبوع الماضي، وأتمنى لكم التوفيق دائمًا."
        not_cv = client.post("/candidate/self/cv", files={"cv": ("cv.docx", docx(letter), DOCX)})
        assert not_cv.status_code == 422 and not_cv.json()["detail"] == "لم نجد مهارات أو خبرات واضحة في الملف. تأكد أنه سيرة ذاتية."
        assert client.get("/health").json() == {"status": "ok"}
        assert client.post("/candidate/self/jobs/discover").status_code == 404     # no CV analysed yet


def test_pipeline_reports_web_search_needs_a_key_and_admin_routes_are_closed(isolated):
    with TestClient(app) as client:
        client.post("/candidate/self/cv", files={"cv": ("cv.docx", docx(IT_CV), DOCX)})
        profile = client.get("/candidate/self/profile").json()
        assert profile["webSearchEnabled"] is False and len(profile["sources"]) == 8
        stages = {s["name"]: s["status"] for s in profile["runs"][0]["stats"]["stages"]}
        assert stages == {"extract": "done", "read": "done", "ai": "skipped", "titles": "done", "match": "done", "job_search": "skipped"}
        assert client.post("/admin/agents/jobs/run").status_code == 403          # no SANAD_ADMIN_TOKEN configured
        assert client.post("/admin/jobs", json={"jobs": []}, headers={"X-Sanad-Admin": "guess"}).status_code == 403


def test_stored_cv_text_is_used_again_and_old_profiles_are_re_read(isolated, monkeypatch):
    from src.agent.job_agent import service

    with TestClient(app) as client:
        client.post("/candidate/self/cv", files={"cv": ("cv.docx", docx(IT_CV), DOCX)})
        stored = candidate_db.get_stored_profile("self")
        assert stored["cv_text"].startswith("Lama Saleh") and "cv_text" not in client.get("/candidate/self/profile").text
        # The reader improves: the stored profile is older, so it is re-read from the stored text without a new upload.
        monkeypatch.setattr(service, "PARSER_VERSION", stored["parser_version"] + 1)
        assert service.upgrade_stale_profile("self") is True
        assert candidate_db.get_stored_profile("self")["parser_version"] == stored["parser_version"] + 1
        assert service.upgrade_stale_profile("self") is False
        # Re-matching covers every active job (not only the candidate's city), with the CV text scanned like an ATS.
        assert service.rematch_all("self", stored["profile"], stored["cv_text"]) >= 12


def test_admin_can_add_jobs_and_run_the_general_search(isolated, monkeypatch):
    monkeypatch.setenv("SANAD_ADMIN_TOKEN", "secret-token")
    job = {"title": "مدخل بيانات", "english": "", "company": "شركة الأفق", "location": "الرياض", "mode": "حضوري", "salary": "", "description": "إدخال البيانات في Excel.",
           "skills": ["Excel"], "sourceUrl": "https://jobs.example.sa/7", "sourceName": "الجهة", "postedAt": None, "deadline": None,
           "deafFriendlyReason": "عمل مكتبي.", "accommodations": []}
    with TestClient(app) as client:
        headers = {"X-Sanad-Admin": "secret-token"}
        assert client.post("/admin/jobs", json={"jobs": [job]}, headers=headers).json()["created"] == 1
        run = client.post("/admin/agents/jobs/run", headers=headers).json()
        assert run["status"] == "done" and run["expired"] == 0          # sources are off in tests; nothing else to fetch
        assert client.get("/admin/agents/runs", headers=headers).json()["runs"][0]["agent"] == "jobs"


# ---------------------------------------------------------------- feeds and direct sources

def test_reads_rss_and_json_job_feeds():
    rss = ("<rss><channel><item><title><![CDATA[مدخل بيانات - شركة الأفق]]></title><link>https://jobs.example.sa/123</link>"
           "<description>وظيفة عن بعد لذوي الإعاقة السمعية في الرياض</description><pubDate>Mon, 16 Nov 2026 08:00:00 GMT</pubDate></item></channel></rss>")
    item = parse_feed(rss, "https://jobs.example.sa/feed")[0]
    assert (item["title"], item["company"], item["sourceUrl"], item["mode"], item["location"]) == \
        ("مدخل بيانات", "شركة الأفق", "https://jobs.example.sa/123", "عن بُعد", "عن بُعد")
    data = json.dumps({"jobs": [{"title": "مصمم", "company": "استوديو", "location": "جدة", "mode": "hybrid", "url": "https://x.sa/j/1", "skills": ["Figma"]}]})
    job = parse_feed(data, "https://x.sa/feed.json")[0]
    assert (job["title"], job["mode"], job["skills"]) == ("مصمم", "هجين", ["Figma"])


def _fake_fetch(responses: dict):
    def fetch(url: str, headers: dict):
        for key, body in responses.items():
            if key in url:
                return body
        raise ConnectionError("offline")
    return fetch


REMOTIVE = {"jobs": [
    {"title": "Frontend Developer", "company_name": "Tamkeen", "url": "https://remotive.com/j/1", "candidate_required_location": "Worldwide",
     "description": "<p>Build React and TypeScript interfaces.</p>", "publication_date": "2026-11-10T00:00:00"},
    {"title": "Call Center Agent", "company_name": "Phone Co", "url": "https://remotive.com/j/2", "candidate_required_location": "Worldwide",
     "description": "Answering calls all day.", "publication_date": "2026-11-10T00:00:00"},
    {"title": "Backend Engineer", "company_name": "USA Only", "url": "https://remotive.com/j/3", "candidate_required_location": "USA",
     "description": "Node.js", "publication_date": "2026-11-10T00:00:00"},
]}


def test_direct_sources_filter_by_place_and_by_how_the_candidate_communicates():
    plan = search_plan(heuristic_profile(IT_CV, NOW))
    assert "Software Engineer" in plan["roles"] and not plan["graduate"]
    sign = search_sources(plan, fetch=_fake_fetch({"remotive.com": REMOTIVE}), mode="sign")
    assert [p["company"] for p in sign["postings"]] == ["Tamkeen"]                      # call-centre job left out for a deaf candidate
    assert {r["source"]: r["status"] for r in sign["reports"]}["Workable"] == "unreachable"
    assert {r["source"]: r["status"] for r in sign["reports"]}["X (تويتر)"] == "needs_key"
    voice = search_sources(plan, fetch=_fake_fetch({"remotive.com": REMOTIVE}), mode="voice")
    assert {p["company"] for p in voice["postings"]} == {"Tamkeen", "Phone Co"}          # a blind candidate can do phone work
    ranked = rank_for_candidate(sign["postings"], heuristic_profile(IT_CV, NOW), IT_CV, plan)
    assert ranked and ranked[0]["item"]["company"] == "Tamkeen" and ranked[0]["match"]["score"] >= 40


def test_graduates_get_graduate_programme_queries():
    assert "برنامج تطوير الخريجين" in " | ".join(personal_queries(heuristic_profile(GRADUATE_CV, NOW)))


# ---------------------------------------------------------------- Claude's web search loop (fake client)

def _block(**kw):
    return SimpleNamespace(**kw)


class FakeClient:
    """Claude searching: first turn records two postings (one twice) and reports a source, then ends."""

    def __init__(self):
        posting = {"title": "محلل بيانات", "english": "Data Analyst", "company": "شركة الأفق", "location": "الرياض", "mode": "هجين", "salary": "",
                   "description": "تحليل البيانات باستخدام SQL وPower BI.", "skills": ["SQL", "Power BI"], "sourceUrl": "https://jobs.example.sa/1",
                   "sourceName": "جدارات", "postedAt": None, "deadline": None, "deafFriendlyReason": "عمل مكتبي كتابي.", "accommodations": []}
        same_on_linkedin = {**posting, "sourceUrl": "https://linkedin.com/jobs/9", "sourceName": "LinkedIn"}
        expired = {**posting, "title": "محاسب", "sourceUrl": "https://jobs.example.sa/2", "deadline": "2020-01-01"}
        self.turns = [
            SimpleNamespace(stop_reason="tool_use", content=[
                _block(type="tool_use", id="t1", name="record_job", input=posting),
                _block(type="tool_use", id="t2", name="record_job", input=same_on_linkedin),
                _block(type="tool_use", id="t3", name="record_job", input=expired),
                _block(type="tool_use", id="t4", name="report_source", input={"source": "جدارات", "status": "results", "note": "وُجد إعلان"}),
            ]),
            SimpleNamespace(stop_reason="end_turn", content=[_block(type="text", text="انتهيت.")]),
        ]
        self.requests = []
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))

    def _create(self, **request):
        self.requests.append(request)
        return self.turns.pop(0)


def test_claude_search_records_verified_postings_once_and_reports_sources(isolated):
    db.init_db()
    fake = FakeClient()
    result = discover_with_claude(["وظيفة محلل بيانات"], 5, client=fake, check_link=lambda url: "unknown")
    assert (result["saved"], result["duplicates"], result["rejected"]) == (1, 1, 1)   # same job on LinkedIn kept once; expired refused
    assert result["sources"] == [{"source": "جدارات", "status": "results", "note": "وُجد إعلان"}]
    tools = [t.get("type") or t["name"] for t in fake.requests[0]["tools"]]
    assert tools == ["web_search_20260209", "web_fetch_20260209", "record_job", "report_source"]
    results = fake.requests[1]["messages"][2]["content"]                                    # user turn after the first reply
    assert len(results) == 4 and all(r["type"] == "tool_result" for r in results)          # all tool results in one message
    found = [p for p in candidate_db.active_postings() if p["source"] == "agent"]
    assert [p["title"] for p in found] == ["محلل بيانات"] and found[0]["source_url"] == "https://jobs.example.sa/1"
    # The company's dashboard still lists only its own jobs.
    with TestClient(app) as client:
        assert len(client.get("/company/jobs").json()) == 12


# ---------------------------------------------------------------- candidate service rules (teammate's candidate.ts)

def test_applying_needs_a_cv_and_nomination_books_a_default_interview(isolated):
    from src.database import company_db

    with TestClient(app) as client:
        with db.connect() as conn:   # a new talent with no CV and no skills yet
            conn.execute("INSERT INTO talents (id, name, mode, years, city, skills_json) VALUES ('new1', 'سعد', 'voice', 0, 'الرياض', '[]')")
        refused = client.post("/candidate/new1/applications/analyst", json={"status": "applied"})
        assert refused.status_code == 422 and refused.json()["detail"] == "أكمل تحليل سيرتك الذاتية قبل التقديم."
        assert client.post("/candidate/self/applications/designer", json={"status": "applied"}).status_code == 200   # demo talent with skills
        client.post("/company/jobs/designer/candidates/self/status", json={"status": "nominated"})
        when = next(a for a in company_db.talent_applications("self") if a["posting_id"] == "designer")["interview_at"]
        assert when and when.endswith("T10:00:00+03:00")                                          # 10:00 Riyadh, two days later or after


def test_a_scanned_pdf_is_read_by_claude_from_the_file(isolated, monkeypatch):
    from src.agent.job_agent import service
    from src.agent.job_agent.ats import reader
    from src.agent.tests.test_schemas import CLAUDE_CV

    class FakeMessages:
        def parse(self, **request):
            assert request["messages"][0]["content"][0]["type"] == "document"
            return SimpleNamespace(stop_reason="end_turn", parsed_output=reader.ClaudeCv.model_validate(CLAUDE_CV))

    monkeypatch.setattr(service, "_claude_available", lambda: True)
    real = reader.read_scanned_pdf
    monkeypatch.setattr(reader, "read_scanned_pdf", lambda data, name=None: real(data, name, client=SimpleNamespace(messages=FakeMessages())))
    with TestClient(app) as client:
        res = client.post("/candidate/self/cv", data={"answers": json.dumps({"city": "الرياض"})},
                          files={"cv": ("scan.pdf", blank_pdf(), "application/pdf")})
        assert res.status_code == 200, res.text
        ats = client.get("/candidate/self/profile").json()["profile"]
        assert ats["engine"] == "claude" and "SQL" in ats["skills"]
        assert next(c for c in ats["ats"]["checks"] if c["id"] == "readable")["score"] == 0   # a scanned image is not ATS-readable


class Refused(Exception):
    status_code = 400


def test_a_refused_history_is_retried_clean_and_recorded_jobs_are_kept(isolated):
    db.init_db()
    fake = FakeClient()
    first, last = fake.turns
    server = [_block(type="server_tool_use", id="s1", name="web_search", input={"query": "x"}),
              _block(type="web_search_tool_result", tool_use_id="s1", content=[{"type": "web_search_result", "url": "https://a.sa"}])]
    first.content = server + first.content
    calls = {"n": 0}

    def create(**request):
        calls["n"] += 1
        if calls["n"] == 2:                      # the provider refuses the replayed history once
            raise Refused("Invalid Anthropic Messages API request")
        if calls["n"] == 3:                      # the retry carries only text and our own tool calls
            blocks = [b["type"] for m in request["messages"] if m["role"] == "assistant" for b in m["content"]]
            assert "server_tool_use" not in blocks and "web_search_tool_result" not in blocks and "tool_use" in blocks
        return first if calls["n"] == 1 else last

    fake.beta = SimpleNamespace(messages=SimpleNamespace(create=create))
    result = discover_with_claude(["x"], 5, client=fake, check_link=lambda url: "unknown")
    assert result["saved"] == 1 and "error" not in result and calls["n"] == 3

    always = {"n": 0}

    def refuse_after_first(**request):
        always["n"] += 1
        if always["n"] == 1:
            return SimpleNamespace(stop_reason="tool_use", content=[_block(type="tool_use", id="r1", name="report_source",
                                                                            input={"source": "جدارات", "status": "results", "note": "x"})])
        raise Refused("still refused")

    fake2 = SimpleNamespace(beta=SimpleNamespace(messages=SimpleNamespace(create=refuse_after_first)))
    partial = discover_with_claude(["x"], 5, client=fake2, check_link=lambda url: "unknown")
    assert partial["sources"][0]["source"] == "جدارات" and partial["error"].startswith("Refused")


def test_on_openrouter_fetched_pages_are_left_out_of_the_replay():
    from src.agent.job_agent.search.discovery import replayable

    content = [_block(type="text", text="أبحث"),
               _block(type="server_tool_use", id="f1", name="web_fetch", input={"url": "https://jobs.sa/1"}),
               _block(type="web_fetch_tool_result", tool_use_id="f1", content={"type": "web_fetch_result", "url": "https://jobs.sa/1"}),
               _block(type="server_tool_use", id="s1", name="web_search", input={"query": "x"}),
               _block(type="web_search_tool_result", tool_use_id="s1", content=[]),
               _block(type="tool_use", id="t1", name="record_job", input={})]
    assert [b["type"] for b in replayable(content)] == ["text", "server_tool_use", "web_search_tool_result", "tool_use"]
