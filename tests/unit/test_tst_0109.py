# TST-0109 – CON-0078: Remote API SLO
# Contract: CON-0078
# Spec: SPEC-0023

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from routes.chat import router as chat_router
from routes.remote import router as remote_router


# ── Shared fakes ──────────────────────────────────────────────────────────────

class _AsyncLines:
    def __init__(self, lines: list[bytes]) -> None:
        self._lines = lines
        self._idx = 0

    def __aiter__(self):
        return self

    async def __anext__(self) -> bytes:
        if self._idx >= len(self._lines):
            raise StopAsyncIteration
        v = self._lines[self._idx]
        self._idx += 1
        return v


class _FakeProc:
    def __init__(self, stdout_lines: list[bytes] = ()) -> None:
        self.stdout = _AsyncLines(list(stdout_lines))
        self.stderr = _AsyncLines([])

    async def wait(self) -> int:
        return 0


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


class _FakeMessages:
    def stream(self, **kwargs) -> _FakeAsyncStream:
        return _FakeAsyncStream(["Hi"])


class _FakeClient:
    def __init__(self) -> None:
        self.messages = _FakeMessages()


def _mock_ctx(token="tok", has_vapid=True):
    ctx = MagicMock()
    vapid = {"private_key": "k", "claims_email": "mailto:t@t.com"} if has_vapid else {}
    ctx.get_config.return_value.raw = {
        "pwa": {"auth": {"token": token}, "vapid": vapid}
    }
    ctx.is_blacklisted.return_value = False
    return ctx


def _p95(times: list[float]) -> float:
    s = sorted(times)
    idx = max(0, int(0.95 * len(s)) - 1)
    return s[idx]


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestTST0109:
    # CON-0078: /ws/chat first-token p95 < 200ms (LLM gemockt, 10 Messungen)
    def test_ws_chat_first_token_p95_under_200ms(self) -> None:
        app = FastAPI()
        app.include_router(chat_router)
        ctx = _mock_ctx(token="tok")
        fake_client = _FakeClient()

        async def fake_exec(*args, **kwargs):
            return _FakeProc()

        times: list[float] = []
        with patch("routes.chat.sdd_context", ctx), \
             patch("routes.chat._get_client", return_value=fake_client), \
             patch("routes.chat._exec", new=fake_exec):
            client = TestClient(app)
            for _ in range(10):
                t0 = time.monotonic()
                with client.websocket_connect("/ws/chat") as ws:
                    ws.send_json({"auth": "tok"})
                    ws.send_json({"text": "hello"})
                    frame = ws.receive_json()   # first frame = delta
                elapsed = time.monotonic() - t0
                times.append(elapsed)

        p95 = _p95(times)
        assert p95 < 0.200, f"p95={p95*1000:.0f}ms exceeds 200ms SLO"

    # CON-0078: /api/sdd/run first SSE-Zeile p95 < 1000ms (subprocess gemockt, 10 Messungen)
    def test_sdd_run_first_sse_line_p95_under_1000ms(self) -> None:
        app = FastAPI()
        app.include_router(remote_router)
        ctx = _mock_ctx(token="tok")

        async def fake_exec(*args, **kwargs):
            return _FakeProc(stdout_lines=[b"line1\n"])

        times: list[float] = []
        with patch("routes.remote.sdd_context", ctx), \
             patch("routes.remote._exec", new=fake_exec):
            client = TestClient(app)
            for _ in range(10):
                t0 = time.monotonic()
                response = client.post(
                    "/sdd/run",
                    json={"cmd": "validate"},
                    headers={"Authorization": "Bearer tok"},
                )
                # First data: line appears after the first SSE event
                first_line = next(
                    (l for l in response.text.splitlines() if l.startswith("data:")),
                    None,
                )
                elapsed = time.monotonic() - t0
                times.append(elapsed)
                assert first_line is not None

        p95 = _p95(times)
        assert p95 < 1.000, f"p95={p95*1000:.0f}ms exceeds 1000ms SLO"

    # CON-0078: /api/push/subscribe Response p95 < 100ms (20 Messungen)
    def test_push_subscribe_p95_under_100ms(self) -> None:
        app = FastAPI()
        app.include_router(remote_router)
        ctx = _mock_ctx(token="tok", has_vapid=True)

        times: list[float] = []
        with patch("routes.remote.sdd_context", ctx):
            client = TestClient(app)
            for i in range(20):
                t0 = time.monotonic()
                response = client.post(
                    "/push/subscribe",
                    json={
                        "endpoint": f"https://fcm.example.com/sub{i}",
                        "keys": {"p256dh": "a", "auth": "b"},
                    },
                    headers={"Authorization": "Bearer tok"},
                )
                elapsed = time.monotonic() - t0
                times.append(elapsed)
                assert response.status_code == 201

        p95 = _p95(times)
        assert p95 < 0.100, f"p95={p95*1000:.0f}ms exceeds 100ms SLO"
