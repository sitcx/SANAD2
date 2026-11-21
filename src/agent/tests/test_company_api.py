from __future__ import annotations

from fastapi.testclient import TestClient

from src.agent.api import app


def test_demo_data_and_indicators_come_from_the_database(isolated):
    with TestClient(app) as client:
        jobs = client.get("/company/jobs").json()
        assert len(jobs) == 12
        analyst = next(j for j in jobs if j["id"] == "analyst")
        assert analyst["applicants"] == 5 and analyst["skills"] == ["Excel", "SQL", "تحليل البيانات"]
        overall = client.get("/company/indicators").json()
        assert overall["applicants"] == 25 and overall["hired"] == 6 and overall["postings"] == 12
        assert overall["retention"] == 83                                  # 5 of 6 hires still employed
        assert overall["by_mode"]["sign"]["applicants"] + overall["by_mode"]["voice"]["applicants"] == 25
        assert client.get("/company/indicators", params={"job_id": "analyst"}).json()["hired"] == 2


def test_candidates_are_filtered_and_ranked(isolated):
    with TestClient(app) as client:
        ranked = client.get("/company/jobs/analyst/candidates", params={"min_years": 0}).json()
        assert [c["talent"]["id"] for c in ranked][:2] == ["c1", "self"]       # 100% match, more years first
        assert ranked[0]["match"] == 100 and not ranked[0]["suggested"]
        senior = client.get("/company/jobs/analyst/candidates", params={"min_years": 3}).json()
        assert {c["talent"]["id"] for c in senior} == {"c1", "c4", "c8"}
        sql = client.get("/company/jobs/analyst/candidates", params=[("min_years", 0), ("must_have", "SQL")]).json()
        assert {c["talent"]["id"] for c in sql} == {"c1", "c4", "self"}
        assert client.get("/company/jobs/nope/candidates").status_code == 404


def test_new_job_gets_suggestions_and_the_full_hiring_flow(isolated):
    with TestClient(app) as client:
        res = client.post("/company/jobs", json={"title": "Data Clerk", "skills": ["Excel", "Excel", " "], "min_years": 0})
        assert res.status_code == 201
        job = res.json()
        assert job["skills"] == ["Excel"]
        suggested = client.get(f"/company/jobs/{job['id']}/candidates").json()
        assert suggested and all(c["suggested"] and c["status"] == "available" for c in suggested)

        base = f"/company/jobs/{job['id']}/candidates/c15"
        assert client.post(f"{base}/schedule", json={"interview_at": "2026-12-01T10:00:00+03:00"}).status_code == 422
        assert client.post(f"{base}/status", json={"status": "nominated"}).json()["status"] == "nominated"
        assert client.post(f"{base}/schedule", json={"interview_at": "2026-12-01T10:00:00+03:00"}).status_code == 200
        assert client.post(f"{base}/status", json={"status": "completed"}).status_code == 200
        assert client.post(f"{base}/status", json={"status": "accepted"}).status_code == 200
        # Only the candidate accepts the offer.
        assert client.post(f"{base}/status", json={"status": "hired"}).status_code == 422
        assert client.post(f"/candidate/c15/applications/{job['id']}", json={"status": "hired"}).status_code == 200
        assert client.get("/company/indicators", params={"job_id": job["id"]}).json()["hired"] == 1


def test_rules_and_validation(isolated):
    with TestClient(app) as client:
        assert client.post("/company/jobs", json={"title": "", "skills": ["x"], "min_years": 0}).status_code == 422
        assert client.post("/company/jobs", json={"title": "x", "skills": [], "min_years": 0}).json()["detail"] == \
            "أضف مهارة مطلوبة واحدة على الأقل."
        # Hired is final.
        assert client.post("/company/jobs/analyst/candidates/c4/status", json={"status": "rejected"}).status_code == 422
        assert client.post("/candidate/self/applications/designer", json={"status": "nominated"}).status_code == 422
        assert client.post("/candidate/self/applications/designer", json={"status": "applied"}).status_code == 200
        apps = {a["posting_id"]: a["status"] for a in client.get("/candidate/self/applications").json()}
        assert apps == {"analyst": "nominated", "support": "nominated", "designer": "applied"}
        assert client.put("/company/jobs/analyst/min-years", json={"min_years": 3}).status_code == 200
        assert len(client.get("/company/jobs/analyst/candidates").json()) == 3
        assert client.post("/company/reset").status_code == 200
        assert len(client.get("/company/jobs/analyst/candidates").json()) == 5
