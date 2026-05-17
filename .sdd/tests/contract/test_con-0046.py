# AUTO-GENERATED from CON-0046 via sdd test generate — do not delete
"""Contract-Tests für Pattern Suggestion Schema (CON-0046).

Spec: SPEC-0015 · Contract: CON-0046
"""
from __future__ import annotations

import jsonschema
import pytest

SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["artifact_id", "artifact_type", "generated_at", "pattern_suggestions"],
    "additionalProperties": False,
    "properties": {
        "artifact_id":   {"type": "string", "pattern": "^(SPEC|CON)-[0-9]{4,}$"},
        "artifact_type": {"type": "string", "enum": ["spec", "contract"]},
        "generated_at":  {"type": "string"},
        "pattern_suggestions": {
            "type": "array",
            "minItems": 0,
            "maxItems": 4,
            "items": {
                "type": "object",
                "required": [
                    "pattern_name", "category", "refactoring_guru_url",
                    "applies_to", "rationale", "alternative", "effort", "priority",
                ],
                "additionalProperties": False,
                "properties": {
                    "pattern_name":         {"type": "string", "minLength": 1},
                    "category":             {"type": "string", "enum": ["Creational", "Structural", "Behavioral"]},
                    "refactoring_guru_url": {"type": "string", "pattern": "^https://refactoring\\.guru/"},
                    "applies_to":           {"type": "string", "minLength": 1},
                    "rationale":            {"type": "string", "minLength": 10},
                    "alternative":          {"type": "string", "minLength": 10},
                    "effort":               {"type": "string", "enum": ["low", "medium", "high"]},
                    "priority":             {"type": "string", "enum": ["recommended", "optional", "consider"]},
                },
            },
        },
    },
}

VALID_INSTANCE = {
    "artifact_id": "SPEC-0015",
    "artifact_type": "spec",
    "generated_at": "2026-05-15T10:00:00Z",
    "pattern_suggestions": [
        {
            "pattern_name": "Strategy",
            "category": "Behavioral",
            "refactoring_guru_url": "https://refactoring.guru/design-patterns/strategy",
            "applies_to": "SPEC-0015 / SolidChecker",
            "rationale": "Jeder SOLID-Checker ist ein unabhängiger Algorithmus mit gleichem Interface.",
            "alternative": "Template Method – abgelehnt: keine gemeinsame Basisstruktur.",
            "effort": "low",
            "priority": "recommended",
        }
    ],
}


def test_tc01_valid_instance_passes():
    """Valide Instanz besteht Schema-Validierung (CON-0046 INV-01/02)."""
    jsonschema.validate(VALID_INSTANCE, SCHEMA)


def test_tc02_invalid_instance_rejected():
    """Invalide Instanz wird abgelehnt (CON-0046 INV-01/02)."""
    invalid = {
        "artifact_id": "SPEC-0015",
        "artifact_type": "spec",
        "generated_at": "2026-05-15T10:00:00Z",
        "pattern_suggestions": [
            {
                "pattern_name": "Strategy",
                "category": "Unknown",
                "refactoring_guru_url": "http://example.com",
                "applies_to": "",
                "rationale": "kurz",
                "alternative": "nein",
                "effort": "super-fast",
                "priority": "maybe",
            }
        ],
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(invalid, SCHEMA)
