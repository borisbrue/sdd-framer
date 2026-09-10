# AUTO-GENERATED from CON-0027 via sdd test generate — do not delete
"""Contract-Tests für Execution Gate – Web API Endpoints (CON-0027).

Spec: SPEC-0014 · Contract: CON-0027
Prüft alle 8 Gate-Routen: Status, Review-Trigger, Konflikt-Management,
HTTP-Statuscodes und Invarianten.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tool" / "sdd_cli" / "web" / "api"))
sys.path.insert(0, str(REPO_ROOT / "tool"))

os.environ.setdefault("SDD_PROJECT_ROOT", str(REPO_ROOT))

import sdd_context

sdd_context.init(REPO_ROOT)

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

UNLOCKED_SPEC = "SPEC-0014"   # hat pipeline_phase: execute-unlocked, status: approved
LOCKED_SPEC   = "SPEC-0014"   # approved spec; gate phase mocked to non-unlocked in TC-06 tests


# ─── TC-01: GET /api/gate/{spec_id}/status — immer HTTP 200 ──────────────────

def test_tc01_gate_status_returns_200_always():
    """GET /gate/{id}/status gibt HTTP 200 auch ohne Pipeline-JSON (CON-0027 INV-04)."""
    res = client.get("/api/gate/SPEC-NONEXISTENT/status")
    assert res.status_code == 200
    body = res.json()
    assert body["pipeline_phase"] is None
    assert isinstance(body["phase_history"], list)
    assert isinstance(body["blocking_issues"], list)


def test_tc01b_gate_status_returns_phase_for_existing_spec():
    """GET /gate/{id}/status gibt pipeline_phase zurück wenn Pipeline-JSON existiert."""
    res = client.get(f"/api/gate/{UNLOCKED_SPEC}/status")
    assert res.status_code == 200
    assert "pipeline_phase" in res.json()


# ─── TC-02: POST auf Phase-Trigger gibt 409 wenn Vorgänger fehlt ─────────────

def test_tc02_phase_trigger_409_when_predecessor_not_done():
    """POST /gate/{id}/contract-review → 409 wenn Phase 4 nicht ok (CON-0027 INV-01)."""
    with patch("routes.gate.ExecutionGate") as MockGate:
        instance = MockGate.return_value
        instance.can_start_phase.return_value = MagicMock(allowed=False,
                                                           reason="Phase 4 nicht abgeschlossen")
        res = client.post(f"/api/gate/{LOCKED_SPEC}/contract-review")

    assert res.status_code == 409
    assert "Phase" in res.json().get("detail", "")


# ─── TC-03: GET /api/gate/{id}/conflicts — 404 wenn kein Bericht ─────────────

def test_tc03_conflicts_404_when_no_report():
    """GET /gate/{id}/conflicts → 404 wenn kein Konfliktbericht existiert (CON-0027)."""
    res = client.get("/api/gate/SPEC-NONEXISTENT/conflicts")
    assert res.status_code == 404


# ─── TC-04: PATCH /conflicts/{cf_id} — 422 ohne reason bei acknowledge ────────

def test_tc04_conflict_patch_422_without_reason():
    """PATCH /gate/{id}/conflicts/{cf} ohne reason → 422 (CON-0027 INV-02)."""
    with patch("routes.gate.ConflictDetector") as MockDetector:
        instance = MockDetector.return_value
        instance.acknowledge.side_effect = ValueError("reason erforderlich")
        res = client.patch(
            "/api/gate/SPEC-0014/conflicts/CF-0014-001",
            json={"action": "acknowledge"},
        )

    assert res.status_code == 422


# ─── TC-05: PATCH /conflicts/{cf_id} — resolve erfolgreich ──────────────────

def test_tc05_conflict_patch_resolve_success():
    """PATCH /gate/{id}/conflicts/{cf} mit action=resolve → 200 (CON-0027)."""
    with patch("routes.gate.ConflictDetector") as MockDetector:
        instance = MockDetector.return_value
        instance.resolve.return_value = None
        res = client.patch(
            "/api/gate/SPEC-0014/conflicts/CF-0014-001",
            json={"action": "resolve", "resolve_strategy": "extend"},
        )

    assert res.status_code == 200


# ─── TC-06: POST /api/orchestrate — 409 wenn Gate nicht bestanden ─────────────

def _approved_spec_doc(spec_id: str) -> MagicMock:
    """Gibt ein Mock-Spec-Dokument mit status=approved zurück."""
    doc = MagicMock()
    doc.frontmatter = {"id": spec_id, "status": "approved"}
    return doc


def test_tc06_orchestrate_409_when_gate_not_passed():
    """POST /api/orchestrate → 409 wenn pipeline_phase != execute-unlocked (CON-0021 INV-07)."""
    with patch("routes.orchestrate.shutil.which", return_value="/usr/bin/claude"), \
         patch("sdd_cli.frontmatter.parse_safe", return_value=_approved_spec_doc(LOCKED_SPEC)), \
         patch("routes.orchestrate._load_gate_phase", return_value="contracts-review"):
        res = client.post("/api/orchestrate", json={"spec_id": LOCKED_SPEC})

    assert res.status_code == 409
    assert "gate_status" in res.json() or "pipeline_phase" in str(res.json())


def test_tc06b_orchestrate_force_with_reason_succeeds():
    """POST /api/orchestrate mit force+override_reason → 202 trotz Gate (CON-0021 INV-07)."""
    with patch("routes.orchestrate.shutil.which", return_value="/usr/bin/claude"), \
         patch("sdd_cli.frontmatter.parse_safe", return_value=_approved_spec_doc(LOCKED_SPEC)), \
         patch("routes.orchestrate._load_gate_phase", return_value="contracts-review"), \
         patch("routes.orchestrate._run_pipeline_bg"), \
         patch("routes.orchestrate._log_gate_override"):
        res = client.post("/api/orchestrate", json={
            "spec_id": LOCKED_SPEC,
            "force": True,
            "override_reason": "Hotfix für CF-0014-001",
        })

    assert res.status_code == 202


def test_tc06c_orchestrate_force_without_reason_rejected():
    """POST /api/orchestrate mit force aber ohne override_reason → 422 (CON-0025 INV-05)."""
    with patch("routes.orchestrate.shutil.which", return_value="/usr/bin/claude"), \
         patch("sdd_cli.frontmatter.parse_safe", return_value=_approved_spec_doc(LOCKED_SPEC)), \
         patch("routes.orchestrate._load_gate_phase", return_value="contracts-review"):
        res = client.post("/api/orchestrate", json={
            "spec_id": LOCKED_SPEC,
            "force": True,
        })

    assert res.status_code == 422
    assert "override_reason" in str(res.json()).lower()
