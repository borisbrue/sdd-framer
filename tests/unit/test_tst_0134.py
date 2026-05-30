# TST-0134 – FlowSession State Machine Behavior
# Spec: SPEC-0032 · Contract: CON-0115 · Framework: pytest-bdd (scenarios via direct test)

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[2] / "web" / "api"))

from flow_session import FlowSession, FlowSessionStore, get_new_spec_steps


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def store() -> FlowSessionStore:
    return FlowSessionStore()


def _client(store: FlowSessionStore):
    """Minimal TestClient with patched store."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from routes.agent_flow import router
    import routes.agent_flow as af

    original = af.get_flow_session_store
    af.get_flow_session_store = lambda: store
    app = FastAPI()
    app.include_router(router, prefix="/api")
    client = TestClient(app, raise_server_exceptions=False)
    return client, af, original


# ─── Happy Path – new-spec flow ───────────────────────────────────────────────

class TestHappyPath:
    def test_new_spec_happy_path_reaches_done(self, store):
        client, af, orig = _client(store)
        try:
            r = client.post("/api/agent/flow/start", json={"flow_type": "new-spec"})
            assert r.status_code == 200
            assert r.json()["state"] == "awaiting_input"
            session_id = r.json()["session_id"]

            steps = get_new_spec_steps()
            done = False
            for i, _ in enumerate(steps):
                r = client.post(
                    f"/api/agent/flow/{session_id}/reply",
                    json={"answer": f"answer-{i}"},
                )
                assert r.status_code == 200
                done = r.json()["done"]
            assert done is True

            # Verify state via GET
            r = client.get(f"/api/agent/flow/{session_id}")
            assert r.json()["state"] == "done"
        finally:
            af.get_flow_session_store = orig


# ─── Review-Flow delegiert an SPEC-0016-JobStore ─────────────────────────────

class TestReviewFlowDelegation:
    def test_review_flow_returns_job_id_from_analysis_store(self, store):
        client, af, orig = _client(store)
        af._start_review_job = lambda spec_id: "analysis-job-42"
        try:
            r = client.post(
                "/api/agent/flow/start",
                json={"flow_type": "review", "spec_id": "SPEC-0032"},
            )
            session_id = r.json()["session_id"]
            assert r.json()["state"] == "awaiting_decision"

            r = client.post(
                f"/api/agent/flow/{session_id}/reply", json={"answer": "ja"}
            )
            data = r.json()
            assert data["done"] is True
            assert data["job_id"] == "analysis-job-42"
        finally:
            af.get_flow_session_store = orig


# ─── Implement-Flow delegiert an SPEC-0007-PipelineRun ───────────────────────

class TestImplementFlowDelegation:
    def test_implement_flow_returns_pipeline_run_id(self, store):
        client, af, orig = _client(store)
        af._start_implement_job = lambda spec_id: "pipeline-run-99"
        try:
            r = client.post(
                "/api/agent/flow/start",
                json={"flow_type": "implement", "spec_id": "SPEC-0032"},
            )
            session_id = r.json()["session_id"]

            r = client.post(
                f"/api/agent/flow/{session_id}/reply", json={"answer": "ja"}
            )
            data = r.json()
            assert data["done"] is True
            assert data["job_id"] == "pipeline-run-99"
        finally:
            af.get_flow_session_store = orig


# ─── Decision Point (FR-05) ───────────────────────────────────────────────────

class TestDecisionPoint:
    def test_ja_on_mid_job_decision_resumes_flow(self, store):
        """Running job paused at decision point → ja → back to running."""
        client, af, orig = _client(store)
        try:
            s = store.create("review", "SPEC-0032")
            s.state = "awaiting_decision"
            s.job_id = "existing-job-id"
            s.current_prompt = "Pattern annehmen?"
            store.save(s)

            r = client.post(
                f"/api/agent/flow/{s.session_id}/reply", json={"answer": "ja"}
            )
            assert r.status_code == 200
            data = r.json()
            assert data["done"] is False
            assert data["state"] == "running"
        finally:
            af.get_flow_session_store = orig

    def test_nein_on_mid_job_decision_discards_step_not_failed(self, store):
        """Nein at decision point → discard step → running, NOT failed (INV per Gherkin)."""
        client, af, orig = _client(store)
        try:
            s = store.create("review", "SPEC-0032")
            s.state = "awaiting_decision"
            s.job_id = "existing-job-id"
            s.current_prompt = "Pattern annehmen?"
            store.save(s)

            r = client.post(
                f"/api/agent/flow/{s.session_id}/reply", json={"answer": "nein"}
            )
            assert r.status_code == 200
            data = r.json()
            assert data["state"] != "failed"
            assert data["done"] is False
        finally:
            af.get_flow_session_store = orig

    def test_invalid_answer_at_decision_point_422(self, store):
        """INV-02: only ja/nein accepted at awaiting_decision."""
        client, af, orig = _client(store)
        try:
            s = store.create("review", "SPEC-0032")
            r = client.post(
                f"/api/agent/flow/{s.session_id}/reply", json={"answer": "vielleicht"}
            )
            assert r.status_code == 422
        finally:
            af.get_flow_session_store = orig


# ─── PWA-Reconnect (FR-06) ────────────────────────────────────────────────────

class TestPwaReconnect:
    def test_get_returns_full_state_with_answers(self, store):
        """After partial flow progress, GET returns step_index, answers, current_prompt."""
        client, af, orig = _client(store)
        try:
            r1 = client.post("/api/agent/flow/start", json={"flow_type": "new-spec"})
            session_id = r1.json()["session_id"]

            client.post(f"/api/agent/flow/{session_id}/reply", json={"answer": "MySpec"})

            r3 = client.get(f"/api/agent/flow/{session_id}")
            assert r3.status_code == 200
            data = r3.json()
            assert data["step_index"] == 1
            assert data["answers"]["0"] == "MySpec"
            assert "current_prompt" in data
        finally:
            af.get_flow_session_store = orig


# ─── TTL / Invarianten ────────────────────────────────────────────────────────

class TestInvariants:
    def test_inv01_done_session_rejects_reply(self, store):
        """INV-01: done session returns 409."""
        client, af, orig = _client(store)
        try:
            s = store.create("new-spec")
            s.state = "done"
            store.save(s)
            r = client.post(f"/api/agent/flow/{s.session_id}/reply", json={"answer": "x"})
            assert r.status_code == 409
        finally:
            af.get_flow_session_store = orig

    def test_inv01_failed_session_rejects_reply(self, store):
        """INV-01: failed session returns 409."""
        client, af, orig = _client(store)
        try:
            s = store.create("new-spec")
            s.state = "failed"
            store.save(s)
            r = client.post(f"/api/agent/flow/{s.session_id}/reply", json={"answer": "x"})
            assert r.status_code == 409
        finally:
            af.get_flow_session_store = orig

    def test_inv03_expired_session_returns_404(self, store):
        """INV-03: TTL-expired session → 404 on GET."""
        client, af, orig = _client(store)
        try:
            s = store.create("new-spec")
            # Backdate to simulate TTL expiry
            s.updated_at = datetime.now(tz=timezone.utc) - timedelta(hours=3)
            store._sessions[s.session_id] = s

            r = client.get(f"/api/agent/flow/{s.session_id}")
            assert r.status_code == 404
        finally:
            af.get_flow_session_store = orig

    def test_inv04_review_job_id_from_external_store_not_own(self, store):
        """INV-04: job_id in reply references mocked external store, not internal."""
        client, af, orig = _client(store)
        external_job_id = "spec-0016-external-job"
        af._start_review_job = lambda spec_id: external_job_id
        try:
            s = store.create("review", "SPEC-0032")
            r = client.post(f"/api/agent/flow/{s.session_id}/reply", json={"answer": "ja"})
            assert r.json()["job_id"] == external_job_id
        finally:
            af.get_flow_session_store = orig

    def test_active_flows_excludes_done_sessions(self, store):
        """active_flows() must not include done/failed sessions."""
        s1 = store.create("new-spec")
        s2 = store.create("hotfix")
        s2.state = "done"
        store.save(s2)

        active = store.active_flows()
        session_ids = [f["session_id"] for f in active]
        assert s1.session_id in session_ids
        assert s2.session_id not in session_ids
