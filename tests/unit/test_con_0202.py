"""TST-0231 – CON-0202: Run-Verzeichnis (run.json, state.json, events, decisions, Anfragen).

Spec: SPEC-0053 · Contract: CON-0202
"""
from __future__ import annotations

from tests.support.quality_project import def_errors

TS = "2026-09-25T10:15:03Z"
STATE = {"run_id": "20260925-101500-a1", "status": "awaiting_supervisor", "phase": "decompose",
         "revisions": 0, "tasks": [], "pending_request_id": "req-1", "updated_at": TS}


def test_tc01_valid_instance_passes():
    """Valide Instanzen aller fünf Dateiarten (CON-0202)."""
    assert def_errors("pipeline_run", "run", {
        "run_id": "r1", "spec_id": "SPEC-0900", "started_at": TS, "sdd_version": "0.1.63",
        "roles": {"decomposer": {"provider": "openai-compat", "model": "q", "role_version": "1.0.0"},
                  "supervisor": {"mode": "session", "role_version": "1.0.0"}},
        "warnings": ["Modell reviewt seine eigene Arbeit"]}) == []
    assert def_errors("pipeline_run", "state", STATE) == []
    assert def_errors("pipeline_run", "event", {"ts": TS, "run_id": "r1", "type": "write_rejected",
                                                "role": "implementer", "detail": {}}) == []
    assert def_errors("pipeline_run", "decision", {
        "ts": TS, "request_id": "req-1", "point": "S1", "source": "session", "valid": True,
        "command": {"point": "S1", "command": "approve", "reason": "ok"}}) == []
    assert def_errors("pipeline_run", "pending_decision", {
        "request_id": "req-1", "point": "S1", "created_at": TS,
        "allowed_commands": ["approve", "revise", "halt"], "facts": {"gate_results": []}}) == []


def test_tc02_invalid_instance_rejected():
    """Beispiel aus dem Contract: unbekannter Status, updated_at fehlt."""
    assert def_errors("pipeline_run", "state", {"run_id": "r", "status": "waiting",
                                                "phase": "decompose", "tasks": []})


def test_inv02_entscheidung_nennt_request_id():
    assert def_errors("pipeline_run", "decision", {
        "ts": TS, "point": "S1", "source": "inline", "valid": True, "command": {}})


def test_inv02_anfrage_braucht_request_id_und_commands():
    assert def_errors("pipeline_run", "pending_decision", {
        "point": "S1", "created_at": TS, "allowed_commands": ["approve"], "facts": {"gate_results": []}})
    assert def_errors("pipeline_run", "pending_decision", {
        "request_id": "r", "point": "S1", "created_at": TS, "allowed_commands": [],
        "facts": {"gate_results": []}})


def test_task_zustaende_geschlossen():
    assert def_errors("pipeline_run", "state", {**STATE, "tasks": [
        {"task_id": "t", "state": "irgendwo", "attempts": 0}]})


def test_inv05_keine_klartext_felder():
    assert def_errors("pipeline_run", "event", {"ts": TS, "run_id": "r", "type": "role_call",
                                                "prompt": "geheim"})
