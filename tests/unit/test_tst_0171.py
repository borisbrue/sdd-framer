# TST-0171
# Contract: CON-0148 – Projektstatus-Datenmodell (v0.1.0)
# Level: unit (offline – validates project objects against JSON Schema)

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

_SCHEMA_PATH = (
    Path(__file__).resolve().parents[2]
    / "contracts" / "data" / "projektstatus-datenmodell.schema.json"
)


@pytest.fixture(scope="module")
def schema() -> dict:
    with open(_SCHEMA_PATH, encoding="utf-8") as fh:
        return json.load(fh)


class TestTST0171:
    """CON-0148: Projektstatus-Datenmodell JSON-Schema validation."""

    def test_schema_file_exists(self):
        assert _SCHEMA_PATH.exists(), f"Schema-Datei nicht gefunden: {_SCHEMA_PATH}"

    # ── Valid objects ─────────────────────────────────────────────────────────

    @pytest.mark.parametrize("status", ["running", "stopped", "starting", "stopping"])
    def test_valid_status_values(self, schema, status):
        jsonschema.validate({"id": "abc", "name": "My Project", "status": status}, schema)

    def test_valid_with_optional_status_changed_at(self, schema):
        jsonschema.validate(
            {"id": "abc", "name": "My Project", "status": "running",
             "statusChangedAt": "2026-06-08T10:00:00Z"},
            schema,
        )

    def test_valid_with_additional_properties(self, schema):
        jsonschema.validate(
            {"id": "abc", "name": "My Project", "status": "stopped",
             "description": "Extra field", "url": "http://example.com"},
            schema,
        )

    # ── Invalid status enum values ────────────────────────────────────────────

    @pytest.mark.parametrize("status", ["unknown", "error", "paused", "", "Running", "STOPPED"])
    def test_invalid_status_enum_raises(self, schema, status):
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate({"id": "abc", "name": "My Project", "status": status}, schema)

    def test_status_null_raises(self, schema):
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate({"id": "abc", "name": "My Project", "status": None}, schema)

    def test_status_trailing_space_raises(self, schema):
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate({"id": "abc", "name": "My Project", "status": "running "}, schema)

    def test_status_as_array_raises(self, schema):
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate({"id": "abc", "name": "My Project", "status": ["running"]}, schema)

    # ── Missing required fields ───────────────────────────────────────────────

    def test_missing_id_raises(self, schema):
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate({"name": "My Project", "status": "running"}, schema)

    def test_missing_name_raises(self, schema):
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate({"id": "abc", "status": "running"}, schema)

    def test_missing_status_raises(self, schema):
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate({"id": "abc", "name": "My Project"}, schema)

    def test_empty_object_raises(self, schema):
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate({}, schema)

    def test_unknown_structure_raises(self, schema):
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate({"foo": "bar"}, schema)

    # ── Type errors ───────────────────────────────────────────────────────────

    def test_id_as_integer_raises(self, schema):
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate({"id": 42, "name": "My Project", "status": "running"}, schema)

    def test_id_null_raises(self, schema):
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate({"id": None, "name": "My Project", "status": "running"}, schema)
