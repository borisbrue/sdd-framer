"""Integration-Tests für POST /api/orchestrate + GET /api/pipeline/* — TST-0025.

Contract: CON-0021 · Spec: SPEC-0007
Alle Pipeline-Runs werden gemockt — kein echter claude-Prozess oder Git nötig.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tool" / "sdd_cli" / "web" / "api"))
sys.path.insert(0, str(REPO_ROOT / "tool"))

os.environ.setdefault("SDD_PROJECT_ROOT", str(REPO_ROOT))

import sdd_context
sdd_context.init(REPO_ROOT)

from fastapi.testclient import TestClient
from main import app
import routes.orchestrate as orch

client = TestClient(app)

CLAUDE_BIN = "/usr/bin/claude"
APPROVED_SPEC  = "SPEC-0007"   # status: approved  (live im Projekt)
IMPLEMENTED_SPEC = "SPEC-0003" # status: implemented (live im Projekt)


@pytest.fixture(autouse=True)
def reset_store():
    """Leert _runs und _active vor und nach jedem Test."""
    orch._runs.clear()
    orch._active.clear()
    yield
    orch._runs.clear()
    orch._active.clear()


# ─── TC-01: 202 für approved Spec ────────────────────────────────────────────

def _approved_doc(spec_id: str):
    from unittest.mock import MagicMock
    doc = MagicMock()
    doc.frontmatter = {"id": spec_id, "status": "approved"}
    return doc


def test_tc01_approved_spec_returns_202():
    """POST /orchestrate mit approved Spec → 202 + run_id (CON-0021 G-01)."""
    with patch("routes.orchestrate.shutil.which", return_value=CLAUDE_BIN), \
         patch("sdd_cli.frontmatter.parse_safe", return_value=_approved_doc(APPROVED_SPEC)), \
         patch("routes.orchestrate._load_gate_phase", return_value="execute-unlocked"), \
         patch("routes.orchestrate._run_pipeline_bg"):
        res = client.post("/api/orchestrate", json={"spec_id": APPROVED_SPEC})

    assert res.status_code == 202
    body = res.json()
    assert "run_id" in body
    assert body["run_id"].startswith(f"{APPROVED_SPEC}-")


# ─── TC-02: 422 für non-approved Spec ────────────────────────────────────────

def test_tc02_non_approved_spec_returns_422():
    """POST /orchestrate mit implemented Spec → 422 (CON-0021 G-01, INV-05)."""
    with patch("routes.orchestrate.shutil.which", return_value=CLAUDE_BIN):
        res = client.post("/api/orchestrate", json={"spec_id": IMPLEMENTED_SPEC})

    assert res.status_code == 422
    assert "approved" in res.json()["detail"].lower()


# ─── TC-03: 404 für unbekannte Spec ──────────────────────────────────────────

def test_tc03_unknown_spec_returns_404():
    """POST /orchestrate mit nicht existierender Spec → 404 (CON-0021 G-01)."""
    with patch("routes.orchestrate.shutil.which", return_value=CLAUDE_BIN):
        res = client.post("/api/orchestrate", json={"spec_id": "SPEC-9999"})

    assert res.status_code == 404


# ─── TC-04: 409 bei Doppel-Start ─────────────────────────────────────────────

def test_tc04_double_start_returns_409():
    """Zweites POST für dieselbe Spec → 409 (CON-0021 G-01, INV-01)."""
    with patch("routes.orchestrate.shutil.which", return_value=CLAUDE_BIN), \
         patch("sdd_cli.frontmatter.parse_safe", return_value=_approved_doc(APPROVED_SPEC)), \
         patch("routes.orchestrate._load_gate_phase", return_value="execute-unlocked"), \
         patch("routes.orchestrate._run_pipeline_bg"):
        res1 = client.post("/api/orchestrate", json={"spec_id": APPROVED_SPEC})
    assert res1.status_code == 202

    # Lauf bleibt im Store (mock → kein cleanup)
    run_id = res1.json()["run_id"]
    orch._runs[run_id].status = "running"
    orch._active[APPROVED_SPEC] = run_id

    with patch("routes.orchestrate.shutil.which", return_value=CLAUDE_BIN), \
         patch("sdd_cli.frontmatter.parse_safe", return_value=_approved_doc(APPROVED_SPEC)), \
         patch("routes.orchestrate._load_gate_phase", return_value="execute-unlocked"), \
         patch("routes.orchestrate._run_pipeline_bg"):
        res2 = client.post("/api/orchestrate", json={"spec_id": APPROVED_SPEC})

    assert res2.status_code == 409
    assert run_id in res2.json()["detail"]


# ─── TC-05: 503 ohne claude CLI ──────────────────────────────────────────────

def test_tc05_no_claude_returns_503():
    """shutil.which('claude') == None → 503 (CON-0021 INV-05)."""
    with patch("routes.orchestrate.shutil.which", return_value=None):
        res = client.post("/api/orchestrate", json={"spec_id": APPROVED_SPEC})

    assert res.status_code == 503
    assert "claude" in res.json()["detail"].lower()


# ─── TC-06: GET /pipeline/{run_id} → 200 ─────────────────────────────────────

def test_tc06_get_run_returns_200():
    """GET /pipeline/{run_id} für existierenden Run → 200 + Felder (CON-0021 G-02)."""
    run_id = "SPEC-TEST-TC06"
    orch._runs[run_id] = orch.RunState(
        run_id=run_id, spec_id="SPEC-TEST", status="running",
        current_step="Code wird generiert…",
    )

    res = client.get(f"/api/pipeline/{run_id}")

    assert res.status_code == 200
    body = res.json()
    assert body["run_id"] == run_id
    assert body["status"] == "running"
    assert body["current_step"] == "Code wird generiert…"
    assert "attempts" in body


# ─── TC-07: GET /pipeline/{run_id} → 404 ─────────────────────────────────────

def test_tc07_get_unknown_run_returns_404():
    """GET /pipeline/{run_id} für unbekannten Run → 404 (CON-0021 G-02)."""
    res = client.get("/api/pipeline/UNKNOWN-RUN-99999")
    assert res.status_code == 404


# ─── TC-08: GET /pipeline/active → 200 ──────────────────────────────────────

def test_tc08_get_active_returns_200():
    """GET /pipeline/active?spec_id=X mit aktivem Lauf → 200 (CON-0021 G-03)."""
    run_id = "SPEC-TEST-ACTIVE-TC08"
    orch._runs[run_id] = orch.RunState(
        run_id=run_id, spec_id="SPEC-ACTIVE", status="running",
    )
    orch._active["SPEC-ACTIVE"] = run_id

    res = client.get("/api/pipeline/active?spec_id=SPEC-ACTIVE")

    assert res.status_code == 200
    assert res.json()["run_id"] == run_id
    assert res.json()["status"] == "running"


# ─── TC-09: GET /pipeline/active → 404 ──────────────────────────────────────

def test_tc09_get_active_no_run_returns_404():
    """GET /pipeline/active?spec_id=X ohne aktiven Lauf → 404 (CON-0021 G-03)."""
    res = client.get("/api/pipeline/active?spec_id=SPEC-NOT-RUNNING")
    assert res.status_code == 404
