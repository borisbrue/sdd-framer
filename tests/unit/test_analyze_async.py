"""Unit-Tests für analyze_async.py – Async API Endpunkte (SPEC-0016, CON-0049/0052)."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parents[2] / "tool" / "sdd_cli" / "web" / "api"))

from fastapi.testclient import TestClient
from fastapi import FastAPI

from routes.analyze_async import router
from job_store import JobStore, get_job_store
from analysis_repository import AnalysisRepository, PersistedAnalysis
import sdd_context


# ─── App-Fixture ──────────────────────────────────────────────────────────────

def _make_app(tmp_path: Path) -> FastAPI:
    app = FastAPI()
    app.include_router(router, prefix="/api")
    return app


def _mock_config(tmp_path: Path):
    from sdd_cli.config import SddConfig
    cfg = SddConfig(root=tmp_path, raw={})
    (tmp_path / ".sdd" / "templates").mkdir(parents=True, exist_ok=True)
    return cfg


def _make_analysis(doc_id: str = "SPEC-0016") -> PersistedAnalysis:
    return PersistedAnalysis(
        result_id="2026-05-16T12:00:00_abc12345",
        doc_id=doc_id,
        timestamp="2026-05-16T12:00:00Z",
        session_id="sess",
        dismissed_ids=[],
        questions=[{"id": "q-001", "section": "FR", "text": "Q?", "severity": "warning"}],
        issues=[{"section": "NFR", "text": "I.", "severity": "error"}],
        suggestions=[{"text": "S."}],
        usage={"input_tokens": 100, "output_tokens": 50},
    )


# ─── POST /analyze/start ──────────────────────────────────────────────────────

class TestStartAnalysis:
    def test_returns_202_with_job_id(self, tmp_path):
        app = _make_app(tmp_path)
        cfg = _mock_config(tmp_path)
        store = JobStore()

        with patch("routes.analyze_async.get_job_store", return_value=store), \
             patch("routes.analyze_async.get_config", return_value=cfg):
            client = TestClient(app, raise_server_exceptions=False)
            res = client.post("/api/docs/SPEC-0016/analyze/start", json={
                "content": "# SPEC-0016\nsome content",
                "doc_type": "spec",
            })
        assert res.status_code == 202
        body = res.json()
        assert "job_id" in body
        assert body["status"] == "queued"

    def test_returns_400_for_empty_content(self, tmp_path):
        app = _make_app(tmp_path)
        cfg = _mock_config(tmp_path)
        store = JobStore()

        with patch("routes.analyze_async.get_job_store", return_value=store), \
             patch("routes.analyze_async.get_config", return_value=cfg):
            client = TestClient(app, raise_server_exceptions=False)
            res = client.post("/api/docs/SPEC-0016/analyze/start", json={
                "content": "   ",
                "doc_type": "spec",
            })
        assert res.status_code == 422

    def test_returns_400_for_invalid_doc_type(self, tmp_path):
        app = _make_app(tmp_path)
        cfg = _mock_config(tmp_path)
        store = JobStore()

        with patch("routes.analyze_async.get_job_store", return_value=store), \
             patch("routes.analyze_async.get_config", return_value=cfg):
            client = TestClient(app, raise_server_exceptions=False)
            res = client.post("/api/docs/SPEC-0016/analyze/start", json={
                "content": "content",
                "doc_type": "invalid",
            })
        assert res.status_code == 422

    def test_returns_429_when_concurrent_limit_exceeded(self, tmp_path):
        app = _make_app(tmp_path)
        cfg = _mock_config(tmp_path)
        store = JobStore()
        for _ in range(5):
            store.create("SPEC-0016")

        with patch("routes.analyze_async.get_job_store", return_value=store), \
             patch("routes.analyze_async.get_config", return_value=cfg):
            client = TestClient(app, raise_server_exceptions=False)
            res = client.post("/api/docs/SPEC-0016/analyze/start", json={
                "content": "content",
                "doc_type": "spec",
            })
        assert res.status_code == 429

    def test_accepts_dismissed_ids(self, tmp_path):
        app = _make_app(tmp_path)
        cfg = _mock_config(tmp_path)
        store = JobStore()

        with patch("routes.analyze_async.get_job_store", return_value=store), \
             patch("routes.analyze_async.get_config", return_value=cfg):
            client = TestClient(app, raise_server_exceptions=False)
            res = client.post("/api/docs/SPEC-0016/analyze/start", json={
                "content": "# Content",
                "doc_type": "spec",
                "dismissed_ids": ["q-001", "q-002"],
            })
        assert res.status_code == 202


# ─── GET /analyze/status/{job_id} ─────────────────────────────────────────────

class TestGetStatus:
    def test_queued_status(self, tmp_path):
        app = _make_app(tmp_path)
        store = JobStore()
        job = store.create("SPEC-0016")

        with patch("routes.analyze_async.get_job_store", return_value=store):
            client = TestClient(app)
            res = client.get(f"/api/docs/SPEC-0016/analyze/status/{job.job_id}")
        assert res.status_code == 200
        assert res.json()["status"] == "queued"
        assert res.json()["result_id"] is None

    def test_complete_status_has_result_id(self, tmp_path):
        app = _make_app(tmp_path)
        store = JobStore()
        job = store.create("SPEC-0016")
        store.update_running(job.job_id)
        store.update_complete(job.job_id, "2026-05-16T12:00:00_abc12345")

        with patch("routes.analyze_async.get_job_store", return_value=store):
            client = TestClient(app)
            res = client.get(f"/api/docs/SPEC-0016/analyze/status/{job.job_id}")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "complete"
        assert data["result_id"] == "2026-05-16T12:00:00_abc12345"

    def test_failed_status_has_error(self, tmp_path):
        app = _make_app(tmp_path)
        store = JobStore()
        job = store.create("SPEC-0016")
        store.update_running(job.job_id)
        store.update_failed(job.job_id, "LLM timeout")

        with patch("routes.analyze_async.get_job_store", return_value=store):
            client = TestClient(app)
            res = client.get(f"/api/docs/SPEC-0016/analyze/status/{job.job_id}")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "failed"
        assert "LLM timeout" in data["error"]

    def test_unknown_job_id_returns_404(self, tmp_path):
        app = _make_app(tmp_path)
        store = JobStore()

        with patch("routes.analyze_async.get_job_store", return_value=store):
            client = TestClient(app)
            res = client.get("/api/docs/SPEC-0016/analyze/status/nonexistent")
        assert res.status_code == 404


# ─── GET /analyses ────────────────────────────────────────────────────────────

class TestListAnalyses:
    def test_empty_returns_empty_list(self, tmp_path):
        app = _make_app(tmp_path)
        cfg = _mock_config(tmp_path)

        with patch("routes.analyze_async.get_config", return_value=cfg):
            client = TestClient(app)
            res = client.get("/api/docs/SPEC-0016/analyses")
        assert res.status_code == 200
        assert res.json() == []

    def test_lists_saved_analyses(self, tmp_path):
        app = _make_app(tmp_path)
        cfg = _mock_config(tmp_path)
        repo = AnalysisRepository(tmp_path / ".sdd" / "analyses")
        repo.save(_make_analysis())

        with patch("routes.analyze_async.get_config", return_value=cfg), \
             patch("routes.analyze_async._get_repo", return_value=repo):
            client = TestClient(app)
            res = client.get("/api/docs/SPEC-0016/analyses")
        assert res.status_code == 200
        assert len(res.json()) == 1


# ─── GET /analyses/{result_id} ────────────────────────────────────────────────

class TestGetAnalysis:
    def test_returns_full_analysis(self, tmp_path):
        app = _make_app(tmp_path)
        cfg = _mock_config(tmp_path)
        repo = AnalysisRepository(tmp_path / ".sdd" / "analyses")
        a = _make_analysis()
        repo.save(a)

        with patch("routes.analyze_async.get_config", return_value=cfg), \
             patch("routes.analyze_async._get_repo", return_value=repo):
            client = TestClient(app)
            res = client.get(f"/api/docs/SPEC-0016/analyses/{a.result_id}")
        assert res.status_code == 200
        data = res.json()
        assert data["result_id"] == a.result_id
        assert len(data["questions"]) == 1

    def test_nonexistent_returns_404(self, tmp_path):
        app = _make_app(tmp_path)
        cfg = _mock_config(tmp_path)
        repo = AnalysisRepository(tmp_path / ".sdd" / "analyses")

        with patch("routes.analyze_async.get_config", return_value=cfg), \
             patch("routes.analyze_async._get_repo", return_value=repo):
            client = TestClient(app)
            res = client.get("/api/docs/SPEC-0016/analyses/nonexistent")
        assert res.status_code == 404


# ─── PATCH /analyses/{result_id}/dismiss ─────────────────────────────────────

class TestDismissItem:
    def test_dismiss_returns_200(self, tmp_path):
        app = _make_app(tmp_path)
        cfg = _mock_config(tmp_path)
        repo = AnalysisRepository(tmp_path / ".sdd" / "analyses")
        a = _make_analysis()
        repo.save(a)

        with patch("routes.analyze_async.get_config", return_value=cfg), \
             patch("routes.analyze_async._get_repo", return_value=repo):
            client = TestClient(app)
            res = client.patch(
                f"/api/docs/SPEC-0016/analyses/{a.result_id}/dismiss",
                json={"item_id": "q-001", "dismissed": True},
            )
        assert res.status_code == 200
        assert "q-001" in res.json()["dismissed_ids"]

    def test_undismiss_removes_id(self, tmp_path):
        app = _make_app(tmp_path)
        cfg = _mock_config(tmp_path)
        repo = AnalysisRepository(tmp_path / ".sdd" / "analyses")
        a = _make_analysis()
        a.dismissed_ids = ["q-001"]
        repo.save(a)

        with patch("routes.analyze_async.get_config", return_value=cfg), \
             patch("routes.analyze_async._get_repo", return_value=repo):
            client = TestClient(app)
            res = client.patch(
                f"/api/docs/SPEC-0016/analyses/{a.result_id}/dismiss",
                json={"item_id": "q-001", "dismissed": False},
            )
        assert res.status_code == 200
        assert "q-001" not in res.json()["dismissed_ids"]

    def test_nonexistent_result_returns_404(self, tmp_path):
        app = _make_app(tmp_path)
        cfg = _mock_config(tmp_path)
        repo = AnalysisRepository(tmp_path / ".sdd" / "analyses")

        with patch("routes.analyze_async.get_config", return_value=cfg), \
             patch("routes.analyze_async._get_repo", return_value=repo):
            client = TestClient(app)
            res = client.patch(
                "/api/docs/SPEC-0016/analyses/nonexistent/dismiss",
                json={"item_id": "q-001", "dismissed": True},
            )
        assert res.status_code == 404

    def test_empty_item_id_returns_422(self, tmp_path):
        app = _make_app(tmp_path)
        cfg = _mock_config(tmp_path)
        repo = AnalysisRepository(tmp_path / ".sdd" / "analyses")
        a = _make_analysis()
        repo.save(a)

        with patch("routes.analyze_async.get_config", return_value=cfg), \
             patch("routes.analyze_async._get_repo", return_value=repo):
            client = TestClient(app)
            res = client.patch(
                f"/api/docs/SPEC-0016/analyses/{a.result_id}/dismiss",
                json={"item_id": "", "dismissed": True},
            )
        assert res.status_code == 422
