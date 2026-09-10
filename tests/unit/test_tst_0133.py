# TST-0133 – AgentFlow API Endpoints
# Spec: SPEC-0032 · Contract: CON-0114 · Framework: pytest + httpx/TestClient

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parents[2] / "tool" / "sdd_cli" / "web" / "api"))

from flow_session import FlowSession, FlowSessionStore
from routes.agent_flow import router


def _app(store: FlowSessionStore) -> FastAPI:
    app = FastAPI()
    app.include_router(router, prefix="/api")
    return app


@pytest.fixture
def store() -> FlowSessionStore:
    return FlowSessionStore()


@pytest.fixture
def client(store: FlowSessionStore) -> TestClient:
    import routes.agent_flow as af
    af_store = store

    original = af.get_flow_session_store

    def _patched():
        return af_store

    af.get_flow_session_store = _patched
    try:
        yield TestClient(_app(store), raise_server_exceptions=False)
    finally:
        af.get_flow_session_store = original


# ─── POST /api/agent/flow/start ──────────────────────────────────────────────

class TestStartFlow:
    def test_new_spec_returns_200_with_session_id(self, client):
        r = client.post("/api/agent/flow/start", json={"flow_type": "new-spec"})
        assert r.status_code == 200
        data = r.json()
        assert "session_id" in data
        assert data["state"] == "awaiting_input"
        assert data["prompt"]

    def test_hotfix_returns_200(self, client):
        r = client.post("/api/agent/flow/start", json={"flow_type": "hotfix"})
        assert r.status_code == 200
        data = r.json()
        assert data["state"] == "awaiting_input"

    def test_review_with_spec_id_returns_awaiting_decision(self, client):
        r = client.post("/api/agent/flow/start", json={"flow_type": "review", "spec_id": "SPEC-0032"})
        assert r.status_code == 200
        data = r.json()
        assert "session_id" in data
        assert data["state"] == "awaiting_decision"

    def test_implement_with_spec_id_returns_awaiting_decision(self, client):
        r = client.post("/api/agent/flow/start", json={"flow_type": "implement", "spec_id": "SPEC-0032"})
        assert r.status_code == 200
        assert r.json()["state"] == "awaiting_decision"

    def test_unknown_flow_type_returns_422(self, client):
        r = client.post("/api/agent/flow/start", json={"flow_type": "unknown-type"})
        assert r.status_code == 422

    def test_missing_flow_type_returns_422(self, client):
        r = client.post("/api/agent/flow/start", json={})
        assert r.status_code == 422

    def test_review_without_spec_id_returns_422(self, client):
        r = client.post("/api/agent/flow/start", json={"flow_type": "review"})
        assert r.status_code == 422

    def test_implement_without_spec_id_returns_422(self, client):
        r = client.post("/api/agent/flow/start", json={"flow_type": "implement"})
        assert r.status_code == 422


# ─── POST /api/agent/flow/{session_id}/reply ─────────────────────────────────

class TestReplyFlow:
    def test_unknown_session_returns_404(self, client):
        r = client.post(
            "/api/agent/flow/00000000-0000-0000-0000-000000000000/reply",
            json={"answer": "test"},
        )
        assert r.status_code == 404

    def test_done_session_returns_409(self, client, store):
        s = store.create("new-spec")
        s.state = "done"
        store.save(s)
        r = client.post(f"/api/agent/flow/{s.session_id}/reply", json={"answer": "test"})
        assert r.status_code == 409

    def test_failed_session_returns_409(self, client, store):
        s = store.create("new-spec")
        s.state = "failed"
        store.save(s)
        r = client.post(f"/api/agent/flow/{s.session_id}/reply", json={"answer": "test"})
        assert r.status_code == 409

    def test_running_session_returns_409(self, client, store):
        s = store.create("review", "SPEC-0032")
        s.state = "running"
        s.job_id = "some-job"
        store.save(s)
        r = client.post(f"/api/agent/flow/{s.session_id}/reply", json={"answer": "test"})
        assert r.status_code == 409

    def test_decision_with_invalid_answer_returns_422(self, client, store):
        s = store.create("review", "SPEC-0032")  # starts awaiting_decision
        r = client.post(f"/api/agent/flow/{s.session_id}/reply", json={"answer": "vielleicht"})
        assert r.status_code == 422

    def test_new_spec_reply_returns_next_prompt(self, client):
        r1 = client.post("/api/agent/flow/start", json={"flow_type": "new-spec"})
        session_id = r1.json()["session_id"]
        r2 = client.post(f"/api/agent/flow/{session_id}/reply", json={"answer": "TestSpec"})
        assert r2.status_code == 200
        data = r2.json()
        assert data["done"] is False
        assert data["prompt"]
        assert data["state"] == "awaiting_input"

    def test_new_spec_completes_after_all_steps(self, client):
        r = client.post("/api/agent/flow/start", json={"flow_type": "new-spec"})
        session_id = r.json()["session_id"]
        for ans in ["Title", "feature", "A feature description", "Boris"]:
            r = client.post(f"/api/agent/flow/{session_id}/reply", json={"answer": ans})
        assert r.status_code == 200
        assert r.json()["done"] is True

    def test_review_ja_returns_done_with_job_id(self, client, store):
        s = store.create("review", "SPEC-0032")
        import routes.agent_flow as af
        original = af._start_review_job
        af._start_review_job = lambda spec_id: "mock-job-id"
        try:
            r = client.post(f"/api/agent/flow/{s.session_id}/reply", json={"answer": "ja"})
        finally:
            af._start_review_job = original
        assert r.status_code == 200
        data = r.json()
        assert data["done"] is True
        assert data["job_id"] == "mock-job-id"


# ─── GET /api/agent/flow/{session_id} ────────────────────────────────────────

class TestGetFlowState:
    def test_unknown_session_returns_404(self, client):
        r = client.get("/api/agent/flow/00000000-0000-0000-0000-000000000000")
        assert r.status_code == 404

    def test_returns_full_state(self, client):
        r1 = client.post("/api/agent/flow/start", json={"flow_type": "new-spec"})
        session_id = r1.json()["session_id"]
        r2 = client.get(f"/api/agent/flow/{session_id}")
        assert r2.status_code == 200
        data = r2.json()
        assert data["session_id"] == session_id
        assert data["flow_type"] == "new-spec"
        assert data["step_index"] == 0
        assert "answers" in data

    def test_state_includes_answers_after_reply(self, client):
        r1 = client.post("/api/agent/flow/start", json={"flow_type": "new-spec"})
        session_id = r1.json()["session_id"]
        client.post(f"/api/agent/flow/{session_id}/reply", json={"answer": "MySpec"})
        r3 = client.get(f"/api/agent/flow/{session_id}")
        data = r3.json()
        assert data["answers"]["0"] == "MySpec"
        assert data["step_index"] == 1
