# AUTO-GENERATED from CON-0030 via sdd test generate — do not delete
"""Contract-Tests für Pipeline Phase State JSON Schema (CON-0030).

Spec: SPEC-0014 · Contract: CON-0030
Prüft: Valide/invalide Instanzen, pipeline_phase-Enum, Override-Pflichtfelder,
       Persistenz-Invarianten.
"""
from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

SCHEMA_PATH = (
    Path(__file__).resolve().parents[2]
    / ".sdd" / "contracts" / "data" / "pipeline-phase-state.schema.json"
)


@pytest.fixture(scope="module")
def schema():
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _valid_state(**overrides):
    base = {
        "spec_id": "SPEC-0014",
        "pipeline_phase": "contracts-review",
        "phase_history": [
            {"phase": "spec-draft", "completed_at": "2026-05-14T00:00:00Z", "result": "ok"},
            {"phase": "spec-review", "completed_at": "2026-05-14T00:00:00Z", "result": "ok"},
            {"phase": "contracts-proposed", "completed_at": "2026-05-14T00:00:00Z", "result": "ok"},
            {"phase": "contracts-draft", "completed_at": "2026-05-14T00:00:00Z", "result": "ok"},
            {"phase": "contracts-review", "completed_at": "2026-05-14T00:00:00Z", "result": "ok"},
        ],
        "blocking_issues": [],
        "conflict_report_ref": ".sdd/conflict-reports/SPEC-0014-conflicts.json",
        "override": None,
    }
    base.update(overrides)
    return base


# ─── TC-01: Valide Instanz besteht Schema-Validierung ────────────────────────

def test_tc01_valid_state_passes(schema):
    """Vollständige valide Instanz besteht Validierung (CON-0030)."""
    jsonschema.validate(_valid_state(), schema)


# ─── TC-02: pipeline_phase=null ist erlaubt ───────────────────────────────────

def test_tc02_null_pipeline_phase_allowed(schema):
    """pipeline_phase=null → valide (CON-0030 INV-01)."""
    jsonschema.validate(_valid_state(pipeline_phase=None), schema)


# ─── TC-03: pipeline_phase muss gültiger Phasenname sein ─────────────────────

def test_tc03_invalid_pipeline_phase_rejected(schema):
    """pipeline_phase='unknown-phase' → Schema-Fehler (CON-0030)."""
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(_valid_state(pipeline_phase="unknown-phase"), schema)


@pytest.mark.parametrize("phase", [
    "spec-draft", "spec-review", "contracts-proposed", "contracts-draft",
    "contracts-review", "tests-generated", "regression-ok", "spec-approved",
    "execute-unlocked",
])
def test_tc03b_all_valid_phases_accepted(schema, phase):
    """Alle 9 definierten Phasennamen sind valide (CON-0030)."""
    jsonschema.validate(_valid_state(pipeline_phase=phase), schema)


# ─── TC-04: phase_history-Einträge brauchen phase/completed_at/result ─────────

def test_tc04_history_entry_missing_result_rejected(schema):
    """phase_history-Eintrag ohne 'result' → Schema-Fehler (CON-0030 INV-04)."""
    state = _valid_state()
    del state["phase_history"][0]["result"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(state, schema)


def test_tc04b_invalid_result_value_rejected(schema):
    """result='skipped' → Schema-Fehler (CON-0030 INV-04)."""
    state = _valid_state()
    state["phase_history"][0]["result"] = "skipped"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(state, schema)


@pytest.mark.parametrize("result", ["ok", "failed"])
def test_tc04c_valid_result_values_accepted(schema, result):
    """result=ok/failed → valide (CON-0030 INV-04)."""
    state = _valid_state()
    state["phase_history"][0]["result"] = result
    jsonschema.validate(state, schema)


# ─── TC-05: Override-Objekt braucht reason und triggered_at ──────────────────

def test_tc05_override_without_reason_rejected(schema):
    """Override ohne 'reason' → Schema-Fehler (CON-0030 INV-06)."""
    state = _valid_state()
    state["override"] = {
        "triggered_at": "2026-05-14T15:00:00Z",
        "blocked_phase": "contracts-review",
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(state, schema)


def test_tc05b_override_with_empty_reason_rejected(schema):
    """Override mit reason='' (leer) → Schema-Fehler (CON-0030 INV-06)."""
    state = _valid_state()
    state["override"] = {
        "triggered_at": "2026-05-14T15:00:00Z",
        "reason": "",
        "blocked_phase": "contracts-review",
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(state, schema)


def test_tc05c_valid_override_accepted(schema):
    """Vollständiges Override-Objekt besteht Validierung (CON-0030)."""
    state = _valid_state()
    state["override"] = {
        "triggered_at": "2026-05-14T15:00:00Z",
        "reason": "Hotfix: CF-0014-001 in SPEC-0015",
        "blocked_phase": "contracts-review",
        "operator": "boris",
    }
    jsonschema.validate(state, schema)


# ─── TC-06: Pflichtfelder spec_id/pipeline_phase/phase_history fehlen ─────────

@pytest.mark.parametrize("field", ["spec_id", "pipeline_phase", "phase_history", "blocking_issues"])
def test_tc06_missing_required_field_rejected(schema, field):
    """Fehlende Pflichtfelder → Schema-Fehler (CON-0030)."""
    state = _valid_state()
    del state[field]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(state, schema)


# ─── TC-07: blocking_issues ist leer bei execute-unlocked ────────────────────

def test_tc07_schema_allows_empty_blocking_issues_at_unlocked(schema):
    """blocking_issues=[] bei execute-unlocked ist valide (CON-0030 INV-05)."""
    state = _valid_state(pipeline_phase="execute-unlocked", blocking_issues=[])
    jsonschema.validate(state, schema)
