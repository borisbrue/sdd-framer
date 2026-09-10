# AUTO-GENERATED from CON-0026 via sdd test generate — do not delete
"""Contract-Tests für Contract Conflict Detection – Analyse-Verhalten (CON-0026).

Spec: SPEC-0014 · Contract: CON-0026
Prüft: Konflikterkennung (5 Typen), Auflösungsregeln, Cache-Verhalten,
       Phase-5-Gate-Enforcement.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tool"))


# ─── Fixtures ────────────────────────────────────────────────────────────────

def _write_contract(path: Path, con_id: str, content: str, status: str = "active"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"---\nid: {con_id}\ntitle: Test\ntype: api\nformat: openapi\n"
        f"spec: SPEC-0001\nversion: 0.1.0\nstatus: {status}\n---\n\n{content}\n",
        encoding="utf-8",
    )


# ─── TC-01: Endpoint-Overlap wird erkannt ─────────────────────────────────────

def test_tc01_endpoint_overlap_detected(tmp_path):
    """Zwei Contracts mit identischem HTTP-Verb+Pfad → endpoint-overlap (CON-0026 INV-01)."""
    _write_contract(
        tmp_path / ".sdd" / "contracts" / "api" / "CON-0001.md",
        "CON-0001",
        "## Endpunkte\nPOST /api/gate/SPEC-0001/approve",
    )
    _write_contract(
        tmp_path / ".sdd" / "contracts" / "api" / "CON-0099.md",
        "CON-0099",
        "## Endpunkte\nPOST /api/gate/SPEC-0001/approve",
    )

    from sdd_cli.conflict_detector import ConflictDetector
    detector = ConflictDetector(repo_root=tmp_path)
    with patch.object(detector, "_llm_analyze", return_value=[{
        "id": "CF-TEST-001",
        "type": "endpoint-overlap",
        "severity": "high",
        "new_contract": "CON-0099",
        "conflicting_contract": "CON-0001",
        "detail": "POST /api/gate/SPEC-0001/approve doppelt definiert",
        "affected_specs": ["SPEC-0001"],
        "status": "open",
    }]):
        report = detector.analyze("SPEC-TEST", new_contracts=["CON-0099"])

    assert len(report.conflicts) == 1
    assert report.conflicts[0]["type"] == "endpoint-overlap"
    assert report.conflicts[0]["severity"] == "high"
    assert report.conflicts[0]["conflicting_contract"] == "CON-0001"


# ─── TC-02: Kein Konflikt bei disjunkten Contracts ────────────────────────────

def test_tc02_no_conflict_for_disjoint_contracts(tmp_path):
    """Contracts ohne Überschneidung → leerer Konfliktbericht (CON-0026)."""
    _write_contract(
        tmp_path / ".sdd" / "contracts" / "api" / "CON-0001.md", "CON-0001",
        "## Endpunkte\nGET /api/specs",
    )
    _write_contract(
        tmp_path / ".sdd" / "contracts" / "api" / "CON-0099.md", "CON-0099",
        "## Endpunkte\nPOST /api/gate/status",
    )

    from sdd_cli.conflict_detector import ConflictDetector
    detector = ConflictDetector(repo_root=tmp_path)
    with patch.object(detector, "_llm_analyze", return_value=[]):
        report = detector.analyze("SPEC-TEST", new_contracts=["CON-0099"])

    assert len(report.conflicts) == 0
    assert report.impact_summary["total_conflicts"] == 0


# ─── TC-03: Alle aktiven und draft Contracts werden gescannt ──────────────────

def test_tc03_scans_active_and_draft_contracts(tmp_path):
    """Workspace-Scan erfasst status=active und status=draft (CON-0026 INV-01)."""
    _write_contract(tmp_path / ".sdd" / "contracts" / "api" / "CON-A.md", "CON-A", "active", "active")
    _write_contract(tmp_path / ".sdd" / "contracts" / "api" / "CON-B.md", "CON-B", "draft", "draft")
    _write_contract(tmp_path / ".sdd" / "contracts" / "api" / "CON-C.md", "CON-C", "deprecated", "deprecated")

    from sdd_cli.conflict_detector import ConflictDetector
    detector = ConflictDetector(repo_root=tmp_path)
    scanned = detector._load_workspace_contracts()

    ids = {c["id"] for c in scanned}
    assert "CON-A" in ids
    assert "CON-B" in ids
    assert "CON-C" not in ids


# ─── TC-04: Phase 5 blockiert bei offenem Konflikt ────────────────────────────

def test_tc04_phase5_blocked_with_open_conflict(tmp_path):
    """sdd test generate blockiert wenn Konflikt status=open ist (CON-0026 INV-03)."""
    report = {
        "spec_id": "SPEC-TEST",
        "generated_at": "2026-01-01T00:00:00Z",
        "new_contracts": ["CON-0099"],
        "conflicts": [{"id": "CF-TEST-001", "status": "open", "type": "endpoint-overlap",
                       "severity": "high", "new_contract": "CON-0099",
                       "conflicting_contract": "CON-0001", "detail": "...",
                       "affected_specs": ["SPEC-0001"]}],
        "impact_summary": {"total_conflicts": 1, "high": 1, "medium": 0, "low": 0,
                           "affected_specs_count": 1},
    }
    r = tmp_path / ".sdd" / "conflict-reports" / "SPEC-TEST-conflicts.json"
    r.parent.mkdir(parents=True)
    r.write_text(json.dumps(report), encoding="utf-8")

    from sdd_cli.gate import ExecutionGate
    gate = ExecutionGate(repo_root=tmp_path)
    result = gate.can_start_phase("SPEC-TEST", "tests-generated")
    assert result.allowed is False
    assert "CF-TEST-001" in result.reason


# ─── TC-05: Conflict resolve setzt status auf resolved ────────────────────────

def test_tc05_conflict_resolve_sets_status(tmp_path):
    """sdd conflict resolve setzt status=resolved (CON-0026)."""
    report_path = tmp_path / ".sdd" / "conflict-reports" / "SPEC-TEST-conflicts.json"
    report_path.parent.mkdir(parents=True)
    report = {
        "spec_id": "SPEC-TEST",
        "generated_at": "2026-01-01T00:00:00Z",
        "new_contracts": ["CON-0099"],
        "conflicts": [{"id": "CF-TEST-001", "status": "open", "type": "endpoint-overlap",
                       "severity": "high", "new_contract": "CON-0099",
                       "conflicting_contract": "CON-0001", "detail": "...",
                       "affected_specs": ["SPEC-0001"], "resolution": None}],
        "impact_summary": {"total_conflicts": 1, "high": 1, "medium": 0, "low": 0,
                           "affected_specs_count": 1},
    }
    report_path.write_text(json.dumps(report), encoding="utf-8")

    from sdd_cli.conflict_detector import ConflictDetector
    detector = ConflictDetector(repo_root=tmp_path)
    detector.resolve("SPEC-TEST", "CF-TEST-001", action="extend")

    updated = json.loads(report_path.read_text(encoding="utf-8"))
    conflict = updated["conflicts"][0]
    assert conflict["status"] == "resolved"
    assert conflict["resolution"]["action"] == "extend"
    assert conflict["resolution"]["resolved_at"] is not None


# ─── TC-06: Acknowledge ohne reason wird abgelehnt ────────────────────────────

def test_tc06_acknowledge_without_reason_rejected(tmp_path):
    """sdd conflict acknowledge ohne --reason → ValueError (CON-0026 INV-07)."""
    report_path = tmp_path / ".sdd" / "conflict-reports" / "SPEC-TEST-conflicts.json"
    report_path.parent.mkdir(parents=True)
    report = {
        "spec_id": "SPEC-TEST", "generated_at": "2026-01-01T00:00:00Z",
        "new_contracts": [], "impact_summary": {"total_conflicts": 1, "high": 0,
                                                 "medium": 1, "low": 0, "affected_specs_count": 1},
        "conflicts": [{"id": "CF-TEST-001", "status": "open", "type": "scope-overlap",
                       "severity": "medium", "new_contract": "CON-0025",
                       "conflicting_contract": "CON-0020", "detail": "...",
                       "affected_specs": ["SPEC-0007"], "resolution": None}],
    }
    report_path.write_text(json.dumps(report), encoding="utf-8")

    from sdd_cli.conflict_detector import ConflictDetector
    detector = ConflictDetector(repo_root=tmp_path)
    with pytest.raises(ValueError, match="reason"):
        detector.acknowledge("SPEC-TEST", "CF-TEST-001", reason=None)


# ─── TC-07: Cache-Invalidierung bei Contract-Änderung ─────────────────────────

def test_tc07_cache_invalidated_on_contract_change(tmp_path):
    """Cache wird bei Datei-Hash-Änderung invalidiert (CON-0026 INV-05)."""
    contract_path = tmp_path / ".sdd" / "contracts" / "api" / "CON-A.md"
    _write_contract(contract_path, "CON-A", "GET /api/specs", "active")

    from sdd_cli.conflict_detector import ContractCache
    cache = ContractCache()
    first = cache.load(contract_path)
    contract_path.write_text(contract_path.read_text() + "\n# changed", encoding="utf-8")
    second = cache.load(contract_path)

    assert first["_hash"] != second["_hash"]
