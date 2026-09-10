# TST-0082 – WebSocket /ws/logs/{spec_id} Endpoint
# Contract: CON-0071 (ws-logs-endpoint)
# Spec: SPEC-0022
from __future__ import annotations

import json
from contextlib import contextmanager
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from routes.logs import router
from starlette.websockets import WebSocketDisconnect

from sdd_cli.log_streamer import LogEventBus


def _make_app(bus: LogEventBus) -> FastAPI:
    """Create isolated test app with mocked sdd_context."""
    app = FastAPI()
    app.include_router(router)
    return app


@contextmanager
def _patched_bus(bus: LogEventBus):
    with patch("routes.logs.sdd_context") as mock_ctx:
        mock_ctx.get_log_event_bus.return_value = bus
        yield mock_ctx


class TestTST0082:
    # CON-0071 INV-01: ungültige spec_id → close ohne accept
    def test_invalid_spec_id_rejected(self) -> None:
        bus = LogEventBus()
        with _patched_bus(bus):
            app = _make_app(bus)
            client = TestClient(app)
            with pytest.raises(WebSocketDisconnect):
                # Server should close before/after accept with invalid spec_id
                with client.websocket_connect("/ws/logs/INVALID"):
                    pass

    # CON-0071 G-04: kein aktiver Stream → error-Nachricht + close
    def test_no_stream_sends_error_and_closes(self) -> None:
        bus = LogEventBus()
        # has_stream returns False (no mark_active called)
        with _patched_bus(bus):
            app = _make_app(bus)
            client = TestClient(app)
            with client.websocket_connect("/ws/logs/SPEC-0022") as ws:
                msg = ws.receive_text()
                data = json.loads(msg)
                assert data["error"] == "no_stream"
                assert data["spec_id"] == "SPEC-0022"

    # CON-0071 G-02: Nachrichten haben korrektes JSON-Format
    def test_message_format_json(self) -> None:
        bus = LogEventBus(max_lines=10)
        bus.mark_active("SPEC-0022")
        bus.publish("SPEC-0022", "hello from container")

        with _patched_bus(bus):
            app = _make_app(bus)
            client = TestClient(app)
            with client.websocket_connect("/ws/logs/SPEC-0022") as ws:
                msg = ws.receive_text()
                data = json.loads(msg)
                assert data["spec_id"] == "SPEC-0022"
                assert data["line"] == "hello from container"
                assert "ts" in data
                assert "buffered" in data

    # CON-0071 G-03: Buffer-History wird beim Verbindungsaufbau gesendet (buffered=true)
    def test_buffer_history_sent_on_connect(self) -> None:
        bus = LogEventBus(max_lines=10)
        bus.mark_active("SPEC-0022")
        bus.publish("SPEC-0022", "old-line-1")
        bus.publish("SPEC-0022", "old-line-2")

        with _patched_bus(bus):
            app = _make_app(bus)
            client = TestClient(app)
            with client.websocket_connect("/ws/logs/SPEC-0022") as ws:
                msg1 = json.loads(ws.receive_text())
                msg2 = json.loads(ws.receive_text())
                assert msg1["buffered"] is True
                assert msg2["buffered"] is True
                assert msg1["line"] == "old-line-1"
                assert msg2["line"] == "old-line-2"

    # CON-0071 INV-01: spec_id mit falscher Länge → rejected
    def test_invalid_spec_id_wrong_format(self) -> None:
        bus = LogEventBus()
        with _patched_bus(bus):
            app = _make_app(bus)
            client = TestClient(app)
            with pytest.raises(WebSocketDisconnect):
                with client.websocket_connect("/ws/logs/SPEC-22"):
                    pass
