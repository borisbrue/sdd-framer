# AUTO-GENERATED from CON-0029 via sdd test generate — do not delete
"""Contract-Tests für Conflict Report JSON Schema (CON-0029).

Spec: SPEC-0014 · Contract: CON-0029
Prüft: Valide/invalide JSON-Instanzen gegen das Schema,
       alle Pflichtfelder, CF-ID-Pattern, Severity-Enum, Impact-Konsistenz.
"""
from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

SCHEMA_PATH = (
    Path(__file__).resolve().parents[2]
    / ".sdd" / "contracts" / "data" / "conflict-report.schema.json"
)


@pytest.fixture(scope="module")
def schema():
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _valid_report(**overrides):
    base = {
        "spec_id": "SPEC-0014",
        "generated_at": "2026-05-14T12:00:00Z",
        "new_contracts": ["CON-0025"],
        "conflicts": [
            {
                "id": "CF-0014-001",
                "type": "scope-overlap",
                "severity": "medium",
                "new_contract": "CON-0025",
                "conflicting_contract": "CON-0020",
                "detail": "CON-0020 definiert Execute-Gate ohne Phase-Bedingung",
                "affected_specs": ["SPEC-0007"],
                "status": "open",
                "resolution": None,
            }
        ],
        "impact_summary": {
            "total_conflicts": 1,
            "high": 0,
            "medium": 1,
            "low": 0,
            "affected_specs_count": 1,
        },
    }
    base.update(overrides)
    return base


# ─── TC-01: Valide Instanz besteht Schema-Validierung ────────────────────────

def test_tc01_valid_report_passes(schema):
    """Vollständiger valider Bericht besteht Validierung (CON-0029 INV-01)."""
    jsonschema.validate(_valid_report(), schema)


# ─── TC-02: CF-ID-Pattern muss CF-{NUM}-{NNN} sein ───────────────────────────

def test_tc02_invalid_cf_id_pattern_rejected(schema):
    """id='CF-001' ohne SPEC_NUM → Schema-Fehler (CON-0029 INV-01)."""
    report = _valid_report()
    report["conflicts"][0]["id"] = "CF-001"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(report, schema)


def test_tc02b_valid_cf_id_accepted(schema):
    """id='CF-0014-001' → valide (CON-0029 INV-01)."""
    report = _valid_report()
    report["conflicts"][0]["id"] = "CF-0014-001"
    jsonschema.validate(report, schema)


# ─── TC-03: Severity muss low/medium/high sein ────────────────────────────────

def test_tc03_invalid_severity_rejected(schema):
    """severity='critical' → Schema-Fehler (CON-0029 INV-02)."""
    report = _valid_report()
    report["conflicts"][0]["severity"] = "critical"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(report, schema)


@pytest.mark.parametrize("sev", ["low", "medium", "high"])
def test_tc03b_valid_severities_accepted(schema, sev):
    """severity=low/medium/high → valide (CON-0029 INV-02)."""
    report = _valid_report()
    report["conflicts"][0]["severity"] = sev
    jsonschema.validate(report, schema)


# ─── TC-04: Type muss einer der 5 definierten sein ───────────────────────────

def test_tc04_invalid_type_rejected(schema):
    """type='unknown-type' → Schema-Fehler (CON-0029 INV-03)."""
    report = _valid_report()
    report["conflicts"][0]["type"] = "unknown-type"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(report, schema)


@pytest.mark.parametrize("t", [
    "endpoint-overlap", "field-contradiction", "behavior-contradiction",
    "scope-overlap", "dependency-gap",
])
def test_tc04b_all_valid_types_accepted(schema, t):
    """Alle 5 Konflikttypen sind schema-valide (CON-0029 INV-03)."""
    report = _valid_report()
    report["conflicts"][0]["type"] = t
    jsonschema.validate(report, schema)


# ─── TC-05: Status muss open/resolved/acknowledged sein ──────────────────────

def test_tc05_invalid_status_rejected(schema):
    """status='pending' → Schema-Fehler (CON-0029 INV-04)."""
    report = _valid_report()
    report["conflicts"][0]["status"] = "pending"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(report, schema)


# ─── TC-06: affected_specs darf nicht leer sein ───────────────────────────────

def test_tc06_empty_affected_specs_rejected(schema):
    """affected_specs=[] → Schema-Fehler (CON-0029 INV-05)."""
    report = _valid_report()
    report["conflicts"][0]["affected_specs"] = []
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(report, schema)


# ─── TC-07: Pflichtfelder spec_id/generated_at/conflicts fehlen ──────────────

@pytest.mark.parametrize("missing_field", ["spec_id", "generated_at", "conflicts", "impact_summary"])
def test_tc07_missing_required_field_rejected(schema, missing_field):
    """Fehlende Pflichtfelder → Schema-Fehler (CON-0029)."""
    report = _valid_report()
    del report[missing_field]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(report, schema)


# ─── TC-08: Resolution-Objekt mit action und resolved_at ist valide ──────────

def test_tc08_resolution_object_valid(schema):
    """Ausgefülltes resolution-Objekt besteht Validierung (CON-0029)."""
    report = _valid_report()
    report["conflicts"][0]["status"] = "resolved"
    report["conflicts"][0]["resolution"] = {
        "action": "extend",
        "reason": "CON-0020 erweitert",
        "resolved_at": "2026-05-14T13:00:00Z",
    }
    jsonschema.validate(report, schema)
