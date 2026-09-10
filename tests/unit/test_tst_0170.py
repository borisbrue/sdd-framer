# TST-0170
# Contract: CON-0147 – Hub Projekt-Status & Steuerungs-API
# Level: contract (offline – validates schema conformance using jsonschema)

from __future__ import annotations

from pathlib import Path

import jsonschema
import pytest
import yaml

_OPENAPI_YAML = (
    Path(__file__).resolve().parents[2]
    / "contracts" / "api" / "hub-projekt-status-steuerungs-api.openapi.yaml"
)


def _load_doc() -> dict:
    with open(_OPENAPI_YAML, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _resolve_ref(doc: dict, ref: str) -> dict:
    parts = ref.lstrip("#/").split("/")
    node = doc
    for part in parts:
        node = node[part]
    return node


def _inline_refs(doc: dict, schema: dict) -> dict:
    if "$ref" in schema:
        return _inline_refs(doc, _resolve_ref(doc, schema["$ref"]))
    result: dict = {}
    for key, value in schema.items():
        if isinstance(value, dict):
            result[key] = _inline_refs(doc, value)
        elif isinstance(value, list):
            result[key] = [
                _inline_refs(doc, item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            result[key] = value
    return result


def _schema(doc: dict, name: str) -> dict:
    return _inline_refs(doc, _resolve_ref(doc, f"#/components/schemas/{name}"))


@pytest.fixture(scope="module")
def doc() -> dict:
    return _load_doc()


class TestTST0170:
    """CON-0147: OpenAPI schema conformance tests (offline, jsonschema-based)."""

    def test_openapi_file_exists(self):
        assert _OPENAPI_YAML.exists(), f"OpenAPI-Datei nicht gefunden: {_OPENAPI_YAML}"

    def test_openapi_version_and_structure(self, doc):
        assert doc["openapi"].startswith("3.")
        assert "paths" in doc
        assert "components" in doc and "schemas" in doc["components"]

    # ── Project ──────────────────────────────────────────────────────────────

    def test_project_valid(self, doc):
        jsonschema.validate(
            {"id": "p1", "name": "Web", "status": "running", "updatedAt": "2026-06-08T09:58:00Z"},
            _schema(doc, "Project"),
        )

    def test_project_missing_required_raises(self, doc):
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate({"id": "p1", "name": "Web"}, _schema(doc, "Project"))

    # ── ServerStatus enum ────────────────────────────────────────────────────

    @pytest.mark.parametrize("val", ["running", "stopped", "starting", "stopping", "error"])
    def test_server_status_valid_enum(self, doc, val):
        jsonschema.validate(val, _schema(doc, "ServerStatus"))

    def test_server_status_invalid_enum_raises(self, doc):
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate("unknown", _schema(doc, "ServerStatus"))

    # ── ProjectList ──────────────────────────────────────────────────────────

    def test_project_list_valid(self, doc):
        jsonschema.validate(
            {
                "projects": [
                    {"id": "p1", "name": "Web", "status": "running", "updatedAt": "2026-06-08T09:58:00Z"},
                ],
                "retrievedAt": "2026-06-08T10:00:00Z",
            },
            _schema(doc, "ProjectList"),
        )

    def test_project_list_empty_projects_valid(self, doc):
        jsonschema.validate(
            {"projects": [], "retrievedAt": "2026-06-08T10:00:00Z"},
            _schema(doc, "ProjectList"),
        )

    def test_project_list_missing_retrieved_at_raises(self, doc):
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate({"projects": []}, _schema(doc, "ProjectList"))

    # ── ActionResult ─────────────────────────────────────────────────────────

    @pytest.mark.parametrize("status", ["starting", "stopping"])
    def test_action_result_valid(self, doc, status):
        jsonschema.validate(
            {"projectId": "p1", "status": status, "requestedAt": "2026-06-08T10:00:05Z"},
            _schema(doc, "ActionResult"),
        )

    def test_action_result_missing_field_raises(self, doc):
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate({"projectId": "p1", "status": "starting"}, _schema(doc, "ActionResult"))

    # ── Error ────────────────────────────────────────────────────────────────

    def test_error_valid(self, doc):
        jsonschema.validate(
            {"code": "PROJECT_NOT_FOUND", "message": "Nicht gefunden."},
            _schema(doc, "Error"),
        )

    def test_error_missing_code_raises(self, doc):
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate({"message": "Fehler"}, _schema(doc, "Error"))

    # ── HealthStatus ─────────────────────────────────────────────────────────

    @pytest.mark.parametrize("status", ["ok", "degraded"])
    def test_health_status_valid(self, doc, status):
        jsonschema.validate(
            {"status": status, "timestamp": "2026-06-08T10:00:00Z"},
            _schema(doc, "HealthStatus"),
        )

    def test_health_status_invalid_enum_raises(self, doc):
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(
                {"status": "unknown", "timestamp": "2026-06-08T10:00:00Z"},
                _schema(doc, "HealthStatus"),
            )

    # ── Inline examples in OpenAPI doc ───────────────────────────────────────

    def test_all_openapi_examples_conform_to_schemas(self, doc):
        """Every inline example in the OpenAPI document validates against its schema."""
        for path, path_item in doc.get("paths", {}).items():
            for method, operation in path_item.items():
                if not isinstance(operation, dict):
                    continue
                for status_code, response in operation.get("responses", {}).items():
                    for _media_type, media in response.get("content", {}).items():
                        example = media.get("example")
                        schema_ref = media.get("schema")
                        if example is None or not schema_ref:
                            continue
                        schema = _inline_refs(doc, schema_ref)
                        try:
                            jsonschema.validate(example, schema)
                        except jsonschema.ValidationError as exc:
                            pytest.fail(
                                f"{method.upper()} {path} → {status_code}: "
                                f"example failed validation: {exc.message}"
                            )
