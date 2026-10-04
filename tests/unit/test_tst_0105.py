# TST-0105 – CON-0074: /ws/chat Auth + Streaming-Format
# Contract: CON-0074
# Spec: SPEC-0023

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from routes.chat import router
from starlette.websockets import WebSocketDisconnect

# ── Fake Anthropic async client ───────────────────────────────────────────────

class _FakeAsyncStream:
    def __init__(self, tokens: list[str]) -> None:
        self._tokens = tokens

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    @property
    def text_stream(self):
        async def _gen():
            for t in self._tokens:
                yield t
        return _gen()


class _FakeAsyncClient:
    # Hier standen __init__ und _Messages doppelt hintereinander; wirksam war nur
    # die zweite Fassung (ruff F811). Die erste ist entfernt — Verhalten gleich.
    def __init__(self, tokens: list[str] = ("Hello",)) -> None:
        self.messages = self._Messages(tokens)
        self._tokens = tokens

    class _Messages:
        def __init__(self, tokens):
            self._tokens = tokens

        def stream(self, **kwargs):
            return _FakeAsyncStream(self._tokens)


# Fix: _FakeAsyncClient needs proper __init__
class _FakeClient:
    def __init__(self, tokens: list[str] = ("Hello",)) -> None:
        self.messages = _FakeMessages(tokens)


class _FakeMessages:
    def __init__(self, tokens: list[str]) -> None:
        self._tokens = tokens

    def stream(self, **kwargs) -> _FakeAsyncStream:
        return _FakeAsyncStream(self._tokens)


# ── Fake subprocess ───────────────────────────────────────────────────────────

class _AsyncLines:
    def __init__(self, lines: list[bytes]) -> None:
        self._lines = lines
        self._idx = 0

    def __aiter__(self):
        return self

    async def __anext__(self) -> bytes:
        if self._idx >= len(self._lines):
            raise StopAsyncIteration
        line = self._lines[self._idx]
        self._idx += 1
        return line


class _FakeProc:
    def __init__(self, stdout_lines: list[bytes] = ()) -> None:
        self.stdout = _AsyncLines(list(stdout_lines))
        self.stderr = _AsyncLines([])

    async def wait(self) -> int:
        return 0


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_app() -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    return app


def _mock_ctx(token="valid-tok"):
    ctx = MagicMock()
    ctx.get_config.return_value.raw = {"pwa": {"auth": {"token": token}}}
    ctx.is_blacklisted.return_value = False
    return ctx


class TestTST0105:
    # CON-0074 G-01: Fehlende Auth → WS close code 4001
    def test_missing_auth_closes_with_4001(self) -> None:
        ctx = _mock_ctx(token="valid-tok")
        with patch("routes.chat.sdd_context", ctx):
            client = TestClient(_make_app())
            with pytest.raises(WebSocketDisconnect) as exc_info:
                with client.websocket_connect("/ws/chat") as ws:
                    ws.send_json({})       # no "auth" key
                    ws.receive_json()      # triggers the close
        assert exc_info.value.code == 4001

    # CON-0074 G-01: Falscher Token → WS close code 4001
    def test_wrong_token_closes_with_4001(self) -> None:
        ctx = _mock_ctx(token="correct-tok")
        with patch("routes.chat.sdd_context", ctx):
            client = TestClient(_make_app())
            with pytest.raises(WebSocketDisconnect) as exc_info:
                with client.websocket_connect("/ws/chat") as ws:
                    ws.send_json({"auth": "wrong-tok"})
                    ws.receive_json()
        assert exc_info.value.code == 4001

    # CON-0074 G-03: Streaming-Token hat delta-Feld
    def test_streaming_token_has_delta_field(self) -> None:
        ctx = _mock_ctx(token="tok")
        fake_client = _FakeClient(tokens=["Hello"])
        with patch("routes.chat.sdd_context", ctx), \
             patch("routes.chat._get_client", return_value=fake_client):
            client = TestClient(_make_app())
            with client.websocket_connect("/ws/chat") as ws:
                ws.send_json({"auth": "tok"})
                ws.send_json({"text": "grüß mich"})
                delta = ws.receive_json()
        assert "delta" in delta
        assert delta["delta"] == "Hello"

    # CON-0074 G-04: Command-Output-Frame hat type + line
    def test_command_output_frame_schema(self) -> None:
        ctx = _mock_ctx(token="tok")
        fake_client = _FakeClient(tokens=["ok"])
        fake_proc = _FakeProc(stdout_lines=[b"Building...\n"])

        async def fake_exec(*args, **kwargs):
            return fake_proc

        with patch("routes.chat.sdd_context", ctx), \
             patch("routes.chat._get_client", return_value=fake_client), \
             patch("routes.chat._exec", new=fake_exec):
            client = TestClient(_make_app())
            with client.websocket_connect("/ws/chat") as ws:
                ws.send_json({"auth": "tok"})
                ws.send_json({"text": "start SPEC-0001"})
                frame = ws.receive_json()   # first frame = command_output
        assert frame.get("type") == "command_output"
        assert "line" in frame
        assert frame["line"] == "Building..."

    # CON-0074 G-05: Abschluss-Frame hat type=done
    def test_done_frame_closes_response(self) -> None:
        ctx = _mock_ctx(token="tok")
        fake_client = _FakeClient(tokens=["Hi"])
        with patch("routes.chat.sdd_context", ctx), \
             patch("routes.chat._get_client", return_value=fake_client):
            client = TestClient(_make_app())
            with client.websocket_connect("/ws/chat") as ws:
                ws.send_json({"auth": "tok"})
                ws.send_json({"text": "hello"})
                frames = []
                while True:
                    f = ws.receive_json()
                    frames.append(f)
                    if f.get("type") == "done":
                        break
        types = [f.get("type") for f in frames]
        assert "done" in types

    # CON-0074 G-06: IntentParser läuft vor Claude (Command-Output vor Delta)
    def test_intent_triggers_command_before_claude(self) -> None:
        ctx = _mock_ctx(token="tok")
        fake_client = _FakeClient(tokens=["ok"])
        fake_proc = _FakeProc(stdout_lines=[b"output\n"])

        async def fake_exec(*args, **kwargs):
            return fake_proc

        with patch("routes.chat.sdd_context", ctx), \
             patch("routes.chat._get_client", return_value=fake_client), \
             patch("routes.chat._exec", new=fake_exec):
            client = TestClient(_make_app())
            with client.websocket_connect("/ws/chat") as ws:
                ws.send_json({"auth": "tok"})
                ws.send_json({"text": "start SPEC-0001"})
                frames = []
                while True:
                    f = ws.receive_json()
                    frames.append(f)
                    if f.get("type") == "done":
                        break

        # command_output must appear before any delta
        first_cmd = next((i for i, f in enumerate(frames) if f.get("type") == "command_output"), None)
        first_delta = next((i for i, f in enumerate(frames) if "delta" in f), None)
        assert first_cmd is not None, "No command_output frame received"
        assert first_delta is not None, "No delta frame received"
        assert first_cmd < first_delta


# #128: Jeder Intent zeigt auf einen existierenden, sichtbaren Befehl (oder einen Adapter aus
# routes.remote.sdd_argv); `dev build/up/down` riefen die entfernte `sdd dev`-Gruppe auf.
@pytest.mark.parametrize("text", ["orchestrate SPEC-0001", "start SPEC-0001", "status"])
def test_intent_zeigt_auf_existierenden_befehl(text):
    from routes.chat import _intent_parser
    from routes.remote import sdd_argv

    from sdd_cli.main import cli

    intent = _intent_parser.handle(text)
    assert intent is not None
    befehl = cli.commands.get(sdd_argv(intent.cmd, intent.args)[0])
    assert befehl is not None and not befehl.hidden, intent


@pytest.mark.parametrize("text", ["dev build", "dev up", "dev down"])
def test_dev_intents_gibt_es_nicht_mehr(text):
    from routes.chat import _intent_parser

    assert _intent_parser.handle(text) is None

