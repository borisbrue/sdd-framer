# TST-0172
# Contract: CON-0149 – Hub-Verbindungs-Health-Endpunkt (v0.1.0)
# Level: integration (offline – mocked HTTP, validates online/offline detection logic)

from __future__ import annotations

from pathlib import Path

import jsonschema
import pytest
import yaml

_OPENAPI_PATH = (
    Path(__file__).resolve().parents[2]
    / "contracts" / "api" / "hub-verbindungs-health-endpunkt.openapi.yaml"
)


def _load_openapi() -> dict:
    with open(_OPENAPI_PATH, encoding="utf-8") as fh:
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
            result[key] = [_inline_refs(doc, i) if isinstance(i, dict) else i for i in value]
        else:
            result[key] = value
    return result


# ─── Minimal model of the PWA's hub connection monitor ───────────────────────

class ConnectionState:
    ONLINE = "online"
    OFFLINE = "offline"


class HubHealthChecker:
    def __init__(self, base_url: str, http_get):
        self._base_url = base_url
        self._http_get = http_get
        self.state = ConnectionState.OFFLINE

    def check(self) -> str:
        try:
            status_code, body = self._http_get(f"{self._base_url}/health")
            if status_code == 200 and isinstance(body, dict) and body.get("status") in ("ok", "degraded"):
                self.state = ConnectionState.ONLINE
            else:
                self.state = ConnectionState.OFFLINE
        except Exception:
            self.state = ConnectionState.OFFLINE
        return self.state


@pytest.fixture(scope="module")
def openapi_doc() -> dict:
    return _load_openapi()


class TestTST0172:
    """CON-0149: Hub health endpoint – online/offline detection."""

    def test_openapi_file_exists(self):
        assert _OPENAPI_PATH.exists()

    # ── Online scenarios ──────────────────────────────────────────────────────

    def test_200_ok_body_sets_online(self):
        body = {"status": "ok", "version": "2.4.1", "timestamp": "2026-06-08T10:00:00Z"}
        checker = HubHealthChecker("http://hub", lambda _: (200, body))
        assert checker.check() == ConnectionState.ONLINE

    def test_200_degraded_body_sets_online(self):
        body = {"status": "degraded", "timestamp": "2026-06-08T10:00:00Z"}
        checker = HubHealthChecker("http://hub", lambda _: (200, body))
        assert checker.check() == ConnectionState.ONLINE

    # ── Offline scenarios ─────────────────────────────────────────────────────

    def test_503_sets_offline(self):
        checker = HubHealthChecker("http://hub", lambda _: (503, {}))
        assert checker.check() == ConnectionState.OFFLINE

    def test_network_error_sets_offline(self):
        def _raise(_): raise ConnectionError("refused")
        checker = HubHealthChecker("http://hub", _raise)
        assert checker.check() == ConnectionState.OFFLINE

    def test_timeout_sets_offline(self):
        def _raise(_): raise TimeoutError("timeout")
        checker = HubHealthChecker("http://hub", _raise)
        assert checker.check() == ConnectionState.OFFLINE

    def test_200_malformed_body_sets_offline(self):
        checker = HubHealthChecker("http://hub", lambda _: (200, {"broken": True}))
        assert checker.check() == ConnectionState.OFFLINE

    def test_200_empty_body_sets_offline(self):
        checker = HubHealthChecker("http://hub", lambda _: (200, {}))
        assert checker.check() == ConnectionState.OFFLINE

    # ── Recovery ─────────────────────────────────────────────────────────────

    def test_recovery_offline_then_online(self):
        seq = iter([
            (503, {}),
            (200, {"status": "ok", "timestamp": "2026-06-08T10:00:00Z"}),
        ])
        checker = HubHealthChecker("http://hub", lambda _: next(seq))
        assert checker.check() == ConnectionState.OFFLINE
        assert checker.check() == ConnectionState.ONLINE

    def test_initial_state_is_offline(self):
        checker = HubHealthChecker("http://hub", lambda _: (200, {}))
        assert checker.state == ConnectionState.OFFLINE

    # ── Schema validation ─────────────────────────────────────────────────────

    def test_health_status_schema_accepts_ok(self, openapi_doc):
        schema = _inline_refs(openapi_doc, {"$ref": "#/components/schemas/HealthStatus"})
        jsonschema.validate({"status": "ok", "timestamp": "2026-06-08T10:00:00Z"}, schema)

    def test_health_status_schema_accepts_degraded(self, openapi_doc):
        schema = _inline_refs(openapi_doc, {"$ref": "#/components/schemas/HealthStatus"})
        jsonschema.validate({"status": "degraded", "version": "1.0.0", "timestamp": "2026-06-08T10:00:00Z"}, schema)

    def test_health_status_schema_rejects_unknown_status(self, openapi_doc):
        schema = _inline_refs(openapi_doc, {"$ref": "#/components/schemas/HealthStatus"})
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate({"status": "unknown", "timestamp": "2026-06-08T10:00:00Z"}, schema)

    def test_health_status_schema_rejects_missing_timestamp(self, openapi_doc):
        schema = _inline_refs(openapi_doc, {"$ref": "#/components/schemas/HealthStatus"})
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate({"status": "ok"}, schema)

    def test_all_openapi_examples_conform_to_schemas(self, openapi_doc):
        for path, path_item in openapi_doc.get("paths", {}).items():
            for method, operation in path_item.items():
                if not isinstance(operation, dict):
                    continue
                for status_code, response in operation.get("responses", {}).items():
                    for _media, media in response.get("content", {}).items():
                        example = media.get("example")
                        schema_ref = media.get("schema")
                        if example is None or not schema_ref:
                            continue
                        schema = _inline_refs(openapi_doc, schema_ref)
                        try:
                            jsonschema.validate(example, schema)
                        except jsonschema.ValidationError as exc:
                            pytest.fail(f"{method.upper()} {path} → {status_code}: {exc.message}")
