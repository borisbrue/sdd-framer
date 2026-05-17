# AUTO-GENERATED from CON-0047 via sdd test generate — do not delete
"""Contract-Tests für Pattern Registry Schema (CON-0047).

Spec: SPEC-0015 · Contract: CON-0047
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import jsonschema
import pytest

sys.path.insert(0, str(Path(__file__).parents[4] / "tool"))

from sdd_cli.pattern import PatternRegistry

SPEC_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["spec_id", "generated_at", "patterns"],
    "additionalProperties": False,
    "properties": {
        "spec_id":      {"type": "string", "pattern": "^SPEC-[0-9]{4,}$"},
        "generated_at": {"type": "string"},
        "patterns": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["pattern_name", "status"],
                "additionalProperties": False,
                "properties": {
                    "pattern_name":      {"type": "string", "minLength": 1},
                    "status":            {"type": "string", "enum": ["accepted", "rejected", "under-review"]},
                    "decided_at":        {"type": ["string", "null"]},
                    "acceptance_reason": {"type": ["string", "null"]},
                    "rejection_reason":  {"type": ["string", "null"]},
                    "refactoring_guru_url": {"type": ["string", "null"]},
                },
            },
        },
    },
}

VALID_REGISTRY = {
    "spec_id": "SPEC-0015",
    "generated_at": "2026-05-15T10:00:00Z",
    "patterns": [
        {
            "pattern_name": "Strategy",
            "status": "accepted",
            "decided_at": "2026-05-15T10:05:00Z",
            "acceptance_reason": "Unabhängige Algorithmen.",
            "rejection_reason": None,
            "refactoring_guru_url": "https://refactoring.guru/design-patterns/strategy",
        },
        {
            "pattern_name": "TemplateMethod",
            "status": "rejected",
            "decided_at": "2026-05-15T10:06:00Z",
            "acceptance_reason": None,
            "rejection_reason": "Keine gemeinsame Basis.",
            "refactoring_guru_url": None,
        },
    ],
}


def test_tc01_valid_instance_passes():
    """Valide Registry-Instanz besteht Schema-Validierung (CON-0047 INV-01/02/03)."""
    jsonschema.validate(VALID_REGISTRY, SPEC_SCHEMA)


def test_tc02_invalid_instance_rejected():
    """INV-02: rejected ohne rejection_reason verletzt Schema (CON-0047)."""
    invalid = {
        "spec_id": "SPEC-0015",
        "generated_at": "2026-05-15T10:00:00Z",
        "patterns": [
            {
                "pattern_name": "Strategy",
                "status": "unknown-status",   # nicht im Enum
            }
        ],
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(invalid, SPEC_SCHEMA)


def test_tc03_registry_accept_persists_correctly():
    """PatternRegistry.accept() schreibt konformes JSON (CON-0047 INV-01..04)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        registry = PatternRegistry(Path(tmpdir))
        registry.accept("SPEC-0015", "Strategy", "Unabhängige Algorithmen.",
                        "https://refactoring.guru/design-patterns/strategy")
        data = json.loads((Path(tmpdir) / ".sdd/patterns/SPEC-0015-patterns.json").read_text())
        jsonschema.validate(data, SPEC_SCHEMA)
        entry = data["patterns"][0]
        assert entry["pattern_name"] == "Strategy"
        assert entry["status"] == "accepted"
        assert entry["acceptance_reason"] == "Unabhängige Algorithmen."
        assert entry["rejection_reason"] is None


def test_tc04_registry_reject_persists_correctly():
    """PatternRegistry.reject() schreibt konformes JSON (CON-0047 INV-02)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        registry = PatternRegistry(Path(tmpdir))
        registry.reject("SPEC-0015", "TemplateMethod", "Keine gemeinsame Basis.")
        data = json.loads((Path(tmpdir) / ".sdd/patterns/SPEC-0015-patterns.json").read_text())
        jsonschema.validate(data, SPEC_SCHEMA)
        entry = data["patterns"][0]
        assert entry["status"] == "rejected"
        assert entry["rejection_reason"] == "Keine gemeinsame Basis."
        assert entry["acceptance_reason"] is None


def test_tc05_pattern_name_unique_per_spec():
    """INV-04: accept+accept desselben Patterns überschreibt statt Duplikat (CON-0047)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        registry = PatternRegistry(Path(tmpdir))
        registry.accept("SPEC-0015", "Strategy", "Grund 1")
        registry.accept("SPEC-0015", "Strategy", "Grund 2 (Update)")
        data = registry.load("SPEC-0015")
        names = [p["pattern_name"] for p in data["patterns"]]
        assert names.count("Strategy") == 1, "Kein Duplikat – nur ein Eintrag pro Pattern"
        assert data["patterns"][0]["acceptance_reason"] == "Grund 2 (Update)"
