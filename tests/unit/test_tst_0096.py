# TST-0096 – CON-0086: POST /api/auth/rotate-token
# Contract: CON-0086
# Spec: SPEC-0025
from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from routes.auth import router


def _make_app() -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    return app


def _mock_ctx(*, current_token: str = "valid-token-hex" * 4, blacklisted: bool = False) -> MagicMock:
    ctx = MagicMock()
    config = MagicMock()
    config.raw = {"pwa": {"auth": {"token": current_token}}}
    config.root = Path("/tmp")
    ctx.get_config.return_value = config
    ctx.is_blacklisted.return_value = blacklisted
    ctx.blacklist_token.return_value = None
    ctx.reload_config.return_value = None
    return ctx


class TestTST0096:
    # CON-0086 G-01: Returns 401 without Authorization header
    def test_missing_auth_returns_401(self) -> None:
        with patch("routes.auth.sdd_context", _mock_ctx()):
            with patch("routes.auth._write_config_atomic"):
                client = TestClient(_make_app())
                response = client.post("/auth/rotate-token")
        assert response.status_code == 401

    # CON-0086 G-01: Returns 401 with wrong token
    def test_wrong_token_returns_401(self) -> None:
        with patch("routes.auth.sdd_context", _mock_ctx(current_token="correct-token")):
            with patch("routes.auth._write_config_atomic"):
                client = TestClient(_make_app())
                response = client.post(
                    "/auth/rotate-token",
                    headers={"Authorization": "Bearer wrong-token"},
                )
        assert response.status_code == 401

    # CON-0086 G-05: blacklisted token returns 401
    def test_blacklisted_token_returns_401(self) -> None:
        token = "old-token-already-rotated"
        with patch("routes.auth.sdd_context", _mock_ctx(current_token=token, blacklisted=True)):
            with patch("routes.auth._write_config_atomic"):
                client = TestClient(_make_app())
                response = client.post(
                    "/auth/rotate-token",
                    headers={"Authorization": f"Bearer {token}"},
                )
        assert response.status_code == 401

    # CON-0086 G-02: new token is 64 hex characters
    def test_new_token_is_64_hex_chars(self) -> None:
        token = "a1b2c3" * 10 + "d4e5"
        with patch("routes.auth.sdd_context", _mock_ctx(current_token=token)):
            with patch("routes.auth._write_config_atomic"):
                client = TestClient(_make_app())
                response = client.post(
                    "/auth/rotate-token",
                    headers={"Authorization": f"Bearer {token}"},
                )
        assert response.status_code == 200
        new_token = response.json()["token"]
        assert len(new_token) == 64
        assert re.fullmatch(r"[0-9a-f]{64}", new_token)

    # CON-0086 G-03: old token is blacklisted after rotation
    def test_old_token_blacklisted_after_rotation(self) -> None:
        token = "b2c3d4" * 10 + "e5f6"
        ctx = _mock_ctx(current_token=token)
        with patch("routes.auth.sdd_context", ctx):
            with patch("routes.auth._write_config_atomic"):
                client = TestClient(_make_app())
                client.post(
                    "/auth/rotate-token",
                    headers={"Authorization": f"Bearer {token}"},
                )
        ctx.blacklist_token.assert_called_once_with(token)

    # CON-0086 G-06: response body is {token: newToken}
    def test_response_body_contains_token_field(self) -> None:
        token = "c3d4e5" * 10 + "f6a7"
        with patch("routes.auth.sdd_context", _mock_ctx(current_token=token)):
            with patch("routes.auth._write_config_atomic"):
                client = TestClient(_make_app())
                response = client.post(
                    "/auth/rotate-token",
                    headers={"Authorization": f"Bearer {token}"},
                )
        data = response.json()
        assert "token" in data
        assert data["token"] != token  # must be a new token
