# TST-0106 – CON-0075: POST /api/sdd/run SSE-Format + Exit-Code
# Contract: CON-0075
# Spec: SPEC-0023

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from routes.remote import router

ALLOWLIST = {"orchestrate", "start", "validate", "contract", "spec", "estimate"}


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
    def __init__(self, stdout_lines=(), stderr_lines=(), rc=0):
        self.stdout = _AsyncLines(list(stdout_lines))
        self.stderr = _AsyncLines(list(stderr_lines))
        self._rc = rc

    async def wait(self) -> int:
        return self._rc


def _make_app() -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    return app


def _mock_ctx(token="valid-tok"):
    ctx = MagicMock()
    ctx.get_config.return_value.raw = {"pwa": {"auth": {"token": token}}}
    ctx.is_blacklisted.return_value = False
    return ctx


def _parse_sse(text: str) -> list[dict]:
    events = []
    for line in text.splitlines():
        if line.startswith("data: "):
            try:
                events.append(json.loads(line[6:]))
            except json.JSONDecodeError:
                pass
    return events


class TestTST0106:
    # CON-0075 G-09: Command-Allowlist enthält genau die spezifizierten Commands
    def test_allowlist_contains_specified_commands(self) -> None:
        from routes.remote import _ALLOWLIST

        expected = {"orchestrate", "start", "validate", "contract", "spec", "estimate"}
        assert expected == ALLOWLIST == _ALLOWLIST

    # #128: Jeder erlaubte Befehl existiert und ist sichtbar (`orchestrate` über sdd_argv)
    def test_allowlist_zeigt_auf_existierende_befehle(self) -> None:
        from routes.remote import _ALLOWLIST, _PUSH_TRIGGER_CMDS, sdd_argv

        from sdd_cli.main import cli

        for cmd in _ALLOWLIST:
            befehl = cli.commands.get(sdd_argv(cmd, ["SPEC-0001"])[0])
            assert befehl is not None and not befehl.hidden, cmd
        assert _PUSH_TRIGGER_CMDS <= _ALLOWLIST and "dev" not in _PUSH_TRIGGER_CMDS

    # CON-0075 G-09: Unbekannte Commands sind nicht in der Allowlist
    def test_unknown_commands_not_in_allowlist(self) -> None:
        for cmd in ["shell", "rm", "exec", "run", "bash"]:
            assert cmd not in ALLOWLIST

    # CON-0075 G-01: Fehlende Auth → HTTP 401
    def test_missing_auth_returns_401(self) -> None:
        with patch("routes.remote.sdd_context", _mock_ctx()):
            client = TestClient(_make_app(), raise_server_exceptions=False)
            response = client.post("/sdd/run", json={"cmd": "validate"})
        assert response.status_code == 401

    # CON-0075 G-03: Unbekannter Command → HTTP 422 unknown_command
    def test_unknown_command_returns_422(self) -> None:
        ctx = _mock_ctx(token="tok")
        with patch("routes.remote.sdd_context", ctx):
            client = TestClient(_make_app(), raise_server_exceptions=False)
            response = client.post(
                "/sdd/run",
                json={"cmd": "shell"},
                headers={"Authorization": "Bearer tok"},
            )
        assert response.status_code == 422
        assert response.json()["detail"] == "unknown_command"

    # CON-0075 G-04: SSE-Event-Format pro Zeile
    def test_sse_line_event_schema(self) -> None:
        ctx = _mock_ctx(token="tok")
        fake_proc = _FakeProc(stdout_lines=[b"Building...\n"], stderr_lines=[])

        async def fake_exec(*args, **kwargs):
            return fake_proc

        with patch("routes.remote.sdd_context", ctx), \
             patch("routes.remote._exec", new=fake_exec):
            client = TestClient(_make_app())
            response = client.post(
                "/sdd/run",
                json={"cmd": "validate"},
                headers={"Authorization": "Bearer tok"},
            )
        events = _parse_sse(response.text)
        line_events = [e for e in events if e.get("type") == "line"]
        assert len(line_events) >= 1
        ev = line_events[0]
        assert ev["data"] == "Building..."
        assert ev["stream"] in ("stdout", "stderr")

    # CON-0075 G-05: Abschluss-Event enthält exit_code
    def test_sse_done_event_has_exit_code(self) -> None:
        ctx = _mock_ctx(token="tok")
        fake_proc = _FakeProc(stdout_lines=[], stderr_lines=[], rc=0)

        async def fake_exec(*args, **kwargs):
            return fake_proc

        with patch("routes.remote.sdd_context", ctx), \
             patch("routes.remote._exec", new=fake_exec):
            client = TestClient(_make_app())
            response = client.post(
                "/sdd/run",
                json={"cmd": "validate"},
                headers={"Authorization": "Bearer tok"},
            )
        events = _parse_sse(response.text)
        done_events = [e for e in events if e.get("type") == "done"]
        assert len(done_events) == 1
        assert "exit_code" in done_events[0]
        assert done_events[0]["exit_code"] == 0

    # CON-0075 G-08: Content-Type ist text/event-stream
    def test_response_content_type_is_event_stream(self) -> None:
        ctx = _mock_ctx(token="tok")
        fake_proc = _FakeProc(stdout_lines=[], stderr_lines=[])

        async def fake_exec(*args, **kwargs):
            return fake_proc

        with patch("routes.remote.sdd_context", ctx), \
             patch("routes.remote._exec", new=fake_exec):
            client = TestClient(_make_app())
            response = client.post(
                "/sdd/run",
                json={"cmd": "validate"},
                headers={"Authorization": "Bearer tok"},
            )
        assert "text/event-stream" in response.headers["content-type"]
