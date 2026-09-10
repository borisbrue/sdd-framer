# TST-0099 – CON-0089: SLO Performance
# Contract: CON-0089 — server-info p95 < 100ms, rotate-token p95 < 500ms
# Spec: SPEC-0025
from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from routes.auth import router


def _make_app() -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    return app


def _mock_ctx(token: str = "a" * 64) -> MagicMock:
    ctx = MagicMock()
    config = MagicMock()
    config.raw = {"project": {"name": "PerfTest"}, "pwa": {"auth": {"token": token}}}
    config.root = Path("/tmp")
    ctx.get_config.return_value = config
    ctx.get_external_url.return_value = ""
    ctx.is_blacklisted.return_value = False
    ctx.blacklist_token.return_value = None
    ctx.reload_config.return_value = None
    return ctx


class TestTST0099:
    # CON-0089: GET /server-info p95 latency < 100ms
    def test_server_info_p95_under_100ms(self) -> None:
        samples = 20
        latencies: list[float] = []
        with patch("routes.auth.sdd_context", _mock_ctx()):
            client = TestClient(_make_app())
            for _ in range(samples):
                t0 = time.monotonic()
                client.get("/server-info")
                latencies.append(time.monotonic() - t0)
        latencies.sort()
        p95_idx = int(len(latencies) * 0.95)
        p95 = latencies[min(p95_idx, len(latencies) - 1)]
        assert p95 < 0.1, f"server-info p95={p95:.3f}s exceeds 100ms SLO"

    # CON-0089: POST /auth/rotate-token p95 latency < 500ms
    def test_rotate_token_p95_under_500ms(self) -> None:
        samples = 10
        latencies: list[float] = []
        token = "b" * 64
        # Each rotation uses a fresh mock so token always matches
        for _ in range(samples):
            with patch("routes.auth.sdd_context", _mock_ctx(token=token)):
                with patch("routes.auth._store_token"):
                    client = TestClient(_make_app())
                    t0 = time.monotonic()
                    client.post(
                        "/auth/rotate-token",
                        headers={"Authorization": f"Bearer {token}"},
                    )
                    latencies.append(time.monotonic() - t0)
        latencies.sort()
        p95_idx = int(len(latencies) * 0.95)
        p95 = latencies[min(p95_idx, len(latencies) - 1)]
        assert p95 < 0.5, f"rotate-token p95={p95:.3f}s exceeds 500ms SLO"
