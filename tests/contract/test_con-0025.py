# AUTO-GENERATED from CON-0025 via sdd test generate — do not delete
"""Contract-Tests für Execution Gate – Phase State Machine (CON-0025).

Spec: SPEC-0014 · Contract: CON-0025
Prüft: Phasenübergänge, Execute-Gate-Enforcement, Force-Override-Verhalten,
       Persistenz und Wiederholbarkeit einzelner Phasen.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tool"))


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def pipeline_json(tmp_path):
    """Erstellt ein minimales Pipeline-JSON für SPEC-TEST."""
    data = {
        "spec_id": "SPEC-TEST",
        "pipeline_phase": "contracts-review",
        "phase_history": [
            {"phase": "spec-draft",          "completed_at": "2026-01-01T00:00:00Z", "result": "ok"},
            {"phase": "spec-review",         "completed_at": "2026-01-01T00:00:00Z", "result": "ok"},
            {"phase": "contracts-proposed",  "completed_at": "2026-01-01T00:00:00Z", "result": "ok"},
            {"phase": "contracts-draft",     "completed_at": "2026-01-01T00:00:00Z", "result": "ok"},
            {"phase": "contracts-review",    "completed_at": "2026-01-01T00:00:00Z", "result": "failed"},
        ],
        "blocking_issues": ["CF-TEST-001 ist noch offen"],
        "conflict_report_ref": None,
        "override": None,
    }
    p = tmp_path / ".sdd" / "pipeline" / "SPEC-TEST-gate.json"
    p.parent.mkdir(parents=True)
    p.write_text(json.dumps(data), encoding="utf-8")
    return p, data


@pytest.fixture
def unlocked_pipeline_json(tmp_path):
    """Pipeline-JSON mit phase=execute-unlocked (alle Phasen grün)."""
    data = {
        "spec_id": "SPEC-TEST",
        "pipeline_phase": "execute-unlocked",
        "phase_history": [
            {"phase": p, "completed_at": "2026-01-01T00:00:00Z", "result": "ok"}
            for p in [
                "spec-draft", "spec-review", "contracts-proposed", "contracts-draft",
                "contracts-review", "tests-generated", "regression-ok", "spec-approved",
                "execute-unlocked",
            ]
        ],
        "blocking_issues": [],
        "conflict_report_ref": None,
        "override": None,
    }
    p = tmp_path / ".sdd" / "pipeline" / "SPEC-TEST-gate.json"
    p.parent.mkdir(parents=True)
    p.write_text(json.dumps(data), encoding="utf-8")
    return p, data


# ─── TC-01: Execute blockiert wenn pipeline_phase != execute-unlocked ─────────

def test_tc01_execute_blocked_when_phase_not_unlocked(pipeline_json, tmp_path):
    """sdd execute gibt Exit-Code 2 zurück wenn phase != execute-unlocked (CON-0025 INV-01)."""
    from sdd_cli.gate import ExecutionGate
    gate = ExecutionGate(repo_root=tmp_path)
    result = gate.check("SPEC-TEST")
    assert result.blocked is True
    assert result.exit_code == 2
    assert "Execution Gate nicht bestanden" in result.message


def test_tc01b_execute_output_contains_phase_overview(pipeline_json, tmp_path):
    """CLI-Output enthält Phasen-Statusübersicht (CON-0025 INV-01)."""
    from sdd_cli.gate import ExecutionGate
    gate = ExecutionGate(repo_root=tmp_path)
    result = gate.check("SPEC-TEST")
    assert "contracts-review" in result.message


# ─── TC-02: Execute freigegeben wenn pipeline_phase == execute-unlocked ────────

def test_tc02_execute_allowed_when_unlocked(unlocked_pipeline_json, tmp_path):
    """sdd execute startet wenn alle Phasen grün (CON-0025 INV-01)."""
    from sdd_cli.gate import ExecutionGate
    gate = ExecutionGate(repo_root=tmp_path)
    result = gate.check("SPEC-TEST")
    assert result.blocked is False
    assert result.exit_code == 0


# ─── TC-03: Force ohne override-reason abgelehnt ──────────────────────────────

def test_tc03_force_without_reason_rejected(pipeline_json, tmp_path):
    """--force ohne --override-reason → Exit-Code 1 (CON-0025 INV-05)."""
    from sdd_cli.gate import ExecutionGate
    gate = ExecutionGate(repo_root=tmp_path)
    result = gate.force_execute("SPEC-TEST", override_reason=None)
    assert result.exit_code == 1
    assert "override-reason" in result.message.lower()


# ─── TC-04: Force mit reason wird akzeptiert und protokolliert ────────────────

def test_tc04_force_with_reason_accepted_and_logged(pipeline_json, tmp_path):
    """--force mit reason startet Execute und schreibt Override ins JSON (CON-0025 INV-06)."""
    json_path, _ = pipeline_json
    from sdd_cli.gate import ExecutionGate
    gate = ExecutionGate(repo_root=tmp_path)
    result = gate.force_execute("SPEC-TEST", override_reason="Hotfix")
    assert result.exit_code == 0

    updated = json.loads(json_path.read_text(encoding="utf-8"))
    assert updated["override"] is not None
    assert updated["override"]["reason"] == "Hotfix"
    assert updated["override"]["triggered_at"] is not None
    assert updated["override"]["blocked_phase"] == "contracts-review"


# ─── TC-05: Phasenübergang blockiert wenn Vorgängerphase fehlt ────────────────

def test_tc05_phase_blocked_when_predecessor_incomplete(tmp_path):
    """Phase 4 nicht startbar wenn Phase 3 nicht ok ist (CON-0025 INV-02)."""
    data = {
        "spec_id": "SPEC-TEST",
        "pipeline_phase": "spec-review",
        "phase_history": [
            {"phase": "spec-draft",  "completed_at": "2026-01-01T00:00:00Z", "result": "ok"},
            {"phase": "spec-review", "completed_at": "2026-01-01T00:00:00Z", "result": "ok"},
        ],
        "blocking_issues": [],
        "conflict_report_ref": None,
        "override": None,
    }
    p = tmp_path / ".sdd" / "pipeline" / "SPEC-TEST-gate.json"
    p.parent.mkdir(parents=True)
    p.write_text(json.dumps(data), encoding="utf-8")

    from sdd_cli.gate import ExecutionGate
    gate = ExecutionGate(repo_root=tmp_path)
    result = gate.can_start_phase("SPEC-TEST", "contracts-draft")
    assert result.allowed is False
    assert "contracts-proposed" in result.reason


# ─── TC-06: Phase kann wiederholt werden ohne vorherige Phasen neu zu starten ──

def test_tc06_phase_rerun_keeps_previous_history(pipeline_json, tmp_path):
    """Wiederholung von Phase 5 behält Phase 1–4 im history (CON-0025 INV-04)."""
    json_path, _ = pipeline_json
    from sdd_cli.gate import ExecutionGate
    gate = ExecutionGate(repo_root=tmp_path)
    gate.mark_phase_started("SPEC-TEST", "contracts-review")

    updated = json.loads(json_path.read_text(encoding="utf-8"))
    phases = [e["phase"] for e in updated["phase_history"]]
    assert "spec-draft" in phases
    assert "spec-review" in phases
    assert "contracts-proposed" in phases
    assert "contracts-draft" in phases


# ─── TC-07: Phasenstatus überlebt Crash (Persistenz nach jedem Abschluss) ──────

def test_tc07_phase_status_persisted_after_completion(tmp_path):
    """Phasenstatus wird sofort nach Abschluss geschrieben (CON-0025 INV-03)."""
    p = tmp_path / ".sdd" / "pipeline" / "SPEC-TEST-gate.json"
    p.parent.mkdir(parents=True)
    p.write_text(json.dumps({
        "spec_id": "SPEC-TEST", "pipeline_phase": None,
        "phase_history": [], "blocking_issues": [],
        "conflict_report_ref": None, "override": None,
    }), encoding="utf-8")

    from sdd_cli.gate import ExecutionGate
    gate = ExecutionGate(repo_root=tmp_path)
    gate.mark_phase_complete("SPEC-TEST", "spec-draft", result="ok")

    written = json.loads(p.read_text(encoding="utf-8"))
    assert written["pipeline_phase"] == "spec-draft"
    assert any(e["phase"] == "spec-draft" and e["result"] == "ok"
               for e in written["phase_history"])
