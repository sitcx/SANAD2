from __future__ import annotations

import json

from fastapi.testclient import TestClient

from src.agent.api import app
from src.database import db


def test_recommend_from_cv_and_db(isolated):
    with TestClient(app) as client:
        cv = "City: Riyadh\nSkills: Excel, SQL, data analysis\n3 years experience".encode()
        res = client.post("/jobs/recommend", files={"cv": ("cv.txt", cv, "text/plain")}, data={"name": "Sara"})
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["status"] == "ok" and body["recommended"][0]["job_id"] == "analyst"
        assert body["candidate_id"] >= 1
        assert {j["id"] for j in db.list_jobs()} == {"analyst", "support", "designer"}


def test_recommend_need_info_and_bad_file(isolated):
    with TestClient(app) as client:
        res = client.post("/jobs/recommend", data={"profile": json.dumps({"skills": ["Figma"]})})
        assert res.json() == {"status": "need_info", "missing_info": ["city"],
                              "profile": {"skills": ["Figma"]}}
        res = client.post("/jobs/recommend", files={"cv": ("cv.exe", b"x", "application/octet-stream")})
        assert res.status_code == 415


def test_interview_websocket(isolated):
    with TestClient(app) as client, client.websocket_connect("/interview/abc") as ws:
        ws.send_json({"type": "start", "mode": "ai", "job_id": "analyst"})
        started = ws.receive_json()
        assert started["type"] == "started"
        ws.send_json({"type": "question", "text": "عرّف بنفسك"})
        assert ws.receive_json()["last_question"] == "عرّف بنفسك"
        ws.send_json({"type": "interpreter"})
        state = ws.receive_json()
        assert state["interpreter_called"] and state["mode"] == "human"
        row = db.get_interview(started["interview_id"])
        assert row["interpreter_called"] == 1 and row["interpreter_reason"] == "button"
