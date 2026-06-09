# AUTO-GENERATED from CON-0159 via sdd test generate — do not delete
"""Contract-Tests für Holdout-Status API Schema-Konformität (CON-0159).

Spec: SPEC-0043 · Contract: CON-0159
Prüft: GET /api/holdouts/{spec_id} Response-Schema, HTTP-Statuscodes,
       Enum-Werte, SSE-Content-Type, Fehlerfälle.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "web" / "api"))
sys.path.insert(0, str(REPO_ROOT / "tool"))

os.environ.setdefault("SDD_PROJECT_ROOT", str(REPO_ROOT))

import sdd_context
sdd_context.init(REPO_ROOT)

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

VALID_STATUS = {"running", "passed", "failed", "none"}


# ─── TC-01: 200 + Pflichtfelder bei vorhandenem Holdout ───────────────────────

def test_tc01_get_holdout_status_200_schema():
    """GET /api/holdouts/{spec_id} liefert 200 mit spec_id, status, updated_at (CON-0159)."""
    with patch("sdd_cli.web.api.routes.holdouts.get_holdout_status") as mock_svc:
        mock_svc.return_value = {
            "spec_id": "SPEC-0043",
            "status": "passed",
            "updated_at": "2026-06-09T12:00:00Z",
            "run_id": "run-001",
            "scenarios": [],
        }
        response = client.get("/api/holdouts/SPEC-0043")

    assert response.status_code == 200
    data = response.json()
    assert "spec_id" in data
    assert "status" in data
    assert "updated_at" in data
    assert data["status"] in VALID_STATUS
    assert data["spec_id"] == "SPEC-0043"


# ─── TC-02: 404 bei nicht vorhandenem Lauf ────────────────────────────────────

def test_tc02_get_holdout_status_404_when_no_run():
    """GET /api/holdouts/SPEC-9999 liefert 404 mit Error-Schema (CON-0159)."""
    with patch("sdd_cli.web.api.routes.holdouts.get_holdout_status") as mock_svc:
        mock_svc.return_value = None
        response = client.get("/api/holdouts/SPEC-9999")

    assert response.status_code == 404
    data = response.json()
    assert "code" in data
    assert "message" in data


# ─── TC-03: 422 bei ungültiger Spec-ID ────────────────────────────────────────

def test_tc03_get_holdout_status_422_invalid_spec_id():
    """GET /api/holdouts/INVALID liefert 422 (CON-0159)."""
    response = client.get("/api/holdouts/INVALID-ID")
    assert response.status_code == 422
    data = response.json()
    assert "code" in data or "detail" in data


# ─── TC-04: SSE-Stream liefert text/event-stream ──────────────────────────────

def test_tc04_sse_stream_content_type():
    """GET /api/holdouts/{spec_id}/stream liefert Content-Type: text/event-stream (CON-0159)."""
    with patch("sdd_cli.web.api.routes.holdouts.stream_holdout_status") as mock_stream:
        mock_stream.return_value = iter([])
        response = client.get("/api/holdouts/SPEC-0043/stream")

    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")


# ─── TC-05: status=failed liefert scenarios-Liste ─────────────────────────────

def test_tc05_failed_status_includes_scenarios():
    """GET bei status=failed liefert scenarios mit name + status (CON-0159 ScenarioResult)."""
    with patch("sdd_cli.web.api.routes.holdouts.get_holdout_status") as mock_svc:
        mock_svc.return_value = {
            "spec_id": "SPEC-0043",
            "status": "failed",
            "updated_at": "2026-06-09T12:00:00Z",
            "run_id": "run-002",
            "scenarios": [
                {"name": "Login", "status": "failed", "error_message": "Expected 200, got 401"},
            ],
        }
        response = client.get("/api/holdouts/SPEC-0043")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "failed"
    assert len(data["scenarios"]) == 1
    scenario = data["scenarios"][0]
    assert "name" in scenario
    assert "status" in scenario
    assert scenario["name"] == "Login"
    assert scenario["status"] in {"passed", "failed"}


# ─── TC-06: status=none → scenarios darf leer/absent sein ────────────────────

def test_tc06_none_status_scenarios_empty():
    """GET bei status=none liefert run_id=null und leere scenarios (CON-0159)."""
    with patch("sdd_cli.web.api.routes.holdouts.get_holdout_status") as mock_svc:
        mock_svc.return_value = {
            "spec_id": "SPEC-0043",
            "status": "none",
            "updated_at": "2026-06-09T12:00:00Z",
            "run_id": None,
            "scenarios": [],
        }
        response = client.get("/api/holdouts/SPEC-0043")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "none"
    assert data["run_id"] is None
    assert data.get("scenarios", []) == []


# ─── TC-07: SSE-Stream 404 bei unbekannter Spec ───────────────────────────────

def test_tc07_sse_stream_404_for_unknown_spec():
    """GET /api/holdouts/SPEC-9999/stream liefert 404 (CON-0159)."""
    with patch("sdd_cli.web.api.routes.holdouts.stream_holdout_status") as mock_stream:
        mock_stream.side_effect = KeyError("SPEC-9999 nicht gefunden")
        response = client.get("/api/holdouts/SPEC-9999/stream")

    assert response.status_code == 404
