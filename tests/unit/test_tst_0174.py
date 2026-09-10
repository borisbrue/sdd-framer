# TST-0174
# Contract: CON-0147 – Hub Projekt-Status & Steuerungs-API (v0.1.0)
# Level: integration (offline – mocked hub, validates polling logic and ≤5s timing)

from __future__ import annotations

import time
from pathlib import Path

import jsonschema
import pytest
import yaml

_OPENAPI_PATH = (
    Path(__file__).resolve().parents[2]
    / "contracts" / "api" / "hub-projekt-status-steuerungs-api.openapi.yaml"
)


def _load_openapi() -> dict:
    with open(_OPENAPI_PATH, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _inline_refs(doc: dict, schema: dict) -> dict:
    if "$ref" in schema:
        parts = schema["$ref"].lstrip("#/").split("/")
        node = doc
        for p in parts:
            node = node[p]
        return _inline_refs(doc, node)
    result: dict = {}
    for key, value in schema.items():
        if isinstance(value, dict):
            result[key] = _inline_refs(doc, value)
        elif isinstance(value, list):
            result[key] = [_inline_refs(doc, i) if isinstance(i, dict) else i for i in value]
        else:
            result[key] = value
    return result


# ─── Exceptions ───────────────────────────────────────────────────────────────

class StatusChangeTimeout(Exception):
    pass


class PreconditionFailed(Exception):
    pass


# ─── Polling helper ───────────────────────────────────────────────────────────

def await_status_change(
    get_status_fn,
    forbidden_status: str,
    timeout_ms: int = 5000,
    interval_ms: int = 250,
) -> tuple[str, float]:
    """Poll until status != forbidden_status. Returns (new_status, elapsed_ms)."""
    t_start = time.monotonic()
    deadline = t_start + timeout_ms / 1000
    while time.monotonic() < deadline:
        status = get_status_fn()
        if status != forbidden_status:
            return status, (time.monotonic() - t_start) * 1000
        time.sleep(interval_ms / 1000)
    raise StatusChangeTimeout(f"Status blieb '{forbidden_status}' nach {timeout_ms} ms")


# ─── Mock Hub ─────────────────────────────────────────────────────────────────

class MockHub:
    def __init__(self, initial_status: str):
        self._status = initial_status
        self._action_response_code: int = 202

    def set_action_response(self, code: int) -> None:
        self._action_response_code = code

    def post_action(self, action: str) -> tuple[int, dict]:
        if self._action_response_code != 202:
            return self._action_response_code, {}
        if action == "start":
            self._status = "starting"
        elif action == "stop":
            self._status = "stopping"
        return 202, {
            "projectId": "proj-001",
            "status": self._status,
            "requestedAt": "2026-06-08T10:00:00Z",
        }

    def get_status(self) -> str:
        return self._status


@pytest.fixture(scope="module")
def openapi_doc() -> dict:
    return _load_openapi()


class TestTST0174:
    """CON-0147: Start/Stopp-Aktion löst Statusänderung innerhalb ≤5s aus."""

    def test_openapi_artifact_exists(self):
        assert _OPENAPI_PATH.exists()

    # ── Szenario 1: stopped → start → starting ───────────────────────────────

    def test_start_returns_202(self):
        hub = MockHub("stopped")
        code, _ = hub.post_action("start")
        assert code == 202

    def test_start_transitions_from_stopped(self):
        hub = MockHub("stopped")
        hub.post_action("start")
        assert hub.get_status() in ("starting", "running")

    def test_start_status_change_within_5s(self):
        hub = MockHub("stopped")
        hub.post_action("start")
        new_status, elapsed_ms = await_status_change(hub.get_status, "stopped", timeout_ms=5000)
        assert new_status in ("starting", "running")
        assert elapsed_ms < 5000

    # ── Szenario 2: running → stop → stopping ────────────────────────────────

    def test_stop_returns_202(self):
        hub = MockHub("running")
        code, _ = hub.post_action("stop")
        assert code == 202

    def test_stop_transitions_from_running(self):
        hub = MockHub("running")
        hub.post_action("stop")
        assert hub.get_status() in ("stopping", "stopped")

    def test_stop_status_change_within_5s(self):
        hub = MockHub("running")
        hub.post_action("stop")
        new_status, elapsed_ms = await_status_change(hub.get_status, "running", timeout_ms=5000)
        assert new_status in ("stopping", "stopped")
        assert elapsed_ms < 5000

    # ── Timeout ───────────────────────────────────────────────────────────────

    def test_polling_timeout_raises_status_change_timeout(self):
        hub = MockHub("stopped")  # status never changes (no action called)
        with pytest.raises(StatusChangeTimeout):
            await_status_change(hub.get_status, "stopped", timeout_ms=100, interval_ms=50)

    # ── 4xx from action endpoint ──────────────────────────────────────────────

    def test_404_action_does_not_change_status(self):
        hub = MockHub("stopped")
        hub.set_action_response(404)
        code, _ = hub.post_action("start")
        assert code == 404
        assert hub.get_status() == "stopped"

    def test_409_signals_invalid_state_transition(self):
        hub = MockHub("running")
        hub.set_action_response(409)
        code, _ = hub.post_action("start")
        assert code == 409

    # ── Precondition: already in transition ──────────────────────────────────

    def test_project_in_starting_is_transition_state(self):
        hub = MockHub("starting")
        assert hub.get_status() in ("starting", "stopping")

    # ── Action result schema conformance ─────────────────────────────────────

    def test_start_action_result_conforms_to_schema(self, openapi_doc):
        hub = MockHub("stopped")
        _, body = hub.post_action("start")
        schema = _inline_refs(openapi_doc, {"$ref": "#/components/schemas/ActionResult"})
        jsonschema.validate(body, schema)

    def test_stop_action_result_conforms_to_schema(self, openapi_doc):
        hub = MockHub("running")
        _, body = hub.post_action("stop")
        schema = _inline_refs(openapi_doc, {"$ref": "#/components/schemas/ActionResult"})
        jsonschema.validate(body, schema)
