# TST-0135 – AgentFlow Tunnel Config Schema
# Spec: SPEC-0032 · Contract: CON-0116 · Framework: pytest + jsonschema

from __future__ import annotations

import json
from pathlib import Path

import pytest

SCHEMA_PATH = (
    Path(__file__).resolve().parents[2]
    / ".sdd"
    / "contracts"
    / "data"
    / "agentflow-tunnel-config-schema.schema.json"
)


@pytest.fixture(scope="module")
def schema() -> dict:
    assert SCHEMA_PATH.exists(), f"Schema-Datei fehlt: {SCHEMA_PATH}"
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


# ─── Gültige Instanzen ────────────────────────────────────────────────────────

@pytest.mark.parametrize("instance", [
    {"tunnel": {"url": "https://sdd.example.com"}},
    {"tunnel": {"url": "https://my-sdd.trycloudflare.com"}},
    {"tunnel": {"url": "https://192.168.1.1:8000"}},
    {"tunnel": {"url": "https://100.64.0.1:8000"}},
])
def test_valid_tunnel_config(schema, instance):
    from jsonschema import validate
    validate(instance=instance, schema=schema)  # raises if invalid


# ─── Ungültige Instanzen – INV-01: muss https:// beginnen ─────────────────────

@pytest.mark.parametrize("instance", [
    {"tunnel": {"url": "http://sdd.example.com"}},    # INV-01: kein HTTPS
    {"tunnel": {"url": ""}},                           # INV-01: leer
    {"tunnel": {"url": "sdd.example.com"}},            # INV-01: kein Schema
    {"tunnel": {"url": "ftp://sdd.example.com"}},      # INV-01: falsches Schema
])
def test_invalid_no_https(schema, instance):
    from jsonschema import ValidationError, validate
    with pytest.raises(ValidationError):
        validate(instance=instance, schema=schema)


# ─── INV-02: kein trailing slash ─────────────────────────────────────────────

def test_invalid_trailing_slash(schema):
    from jsonschema import ValidationError, validate
    with pytest.raises(ValidationError):
        validate(
            instance={"tunnel": {"url": "https://sdd.example.com/"}},
            schema=schema,
        )


# ─── INV-03: keine zusätzlichen Properties ───────────────────────────────────

def test_invalid_additional_properties(schema):
    from jsonschema import ValidationError, validate
    with pytest.raises(ValidationError):
        validate(
            instance={"tunnel": {"url": "https://sdd.example.com", "extra": "x"}},
            schema=schema,
        )


# ─── Pflichtfelder ────────────────────────────────────────────────────────────

def test_missing_url_field(schema):
    from jsonschema import ValidationError, validate
    with pytest.raises(ValidationError):
        validate(instance={"tunnel": {}}, schema=schema)


def test_missing_tunnel_object(schema):
    from jsonschema import ValidationError, validate
    with pytest.raises(ValidationError):
        validate(instance={}, schema=schema)


# ─── Schema-Datei vorhanden ───────────────────────────────────────────────────

def test_schema_file_exists():
    assert SCHEMA_PATH.exists(), f"Schema-Datei fehlt: {SCHEMA_PATH}"


def test_schema_is_valid_json():
    data = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert data.get("$schema")
    assert data.get("properties", {}).get("tunnel")
