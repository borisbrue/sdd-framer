# TST-0095 – CON-0085: GET /api/server-info
# Contract: CON-0085
# Spec: SPEC-0025
from __future__ import annotations

import hashlib
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from routes.auth import router


def _make_app() -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    return app


def _mock_ctx(*, name: str = "MyProject", external_url: str = "", token: str = "") -> MagicMock:
    ctx = MagicMock()
    config = MagicMock()
    config.raw = {"project": {"name": name}, "pwa": {"auth": {"token": token}}}
    ctx.get_config.return_value = config
    ctx.get_external_url.return_value = external_url
    return ctx


class TestTST0095:
    # CON-0085 G-01: Returns 200 without auth header
    def test_no_auth_required(self) -> None:
        with patch("routes.auth.sdd_context", _mock_ctx()):
            client = TestClient(_make_app())
            response = client.get("/server-info")
        assert response.status_code == 200

    # CON-0085 G-01: Response contains required fields
    def test_response_fields_present(self) -> None:
        with patch("routes.auth.sdd_context", _mock_ctx(name="P", external_url="http://x.test", token="abc")):
            client = TestClient(_make_app())
            response = client.get("/server-info")
        data = response.json()
        assert "name" in data
        assert "externalUrl" in data
        assert "tokenHash" in data

    # CON-0085 G-03: tokenHash = SHA-256(token)[:8], never the raw token
    def test_token_hash_is_sha256_prefix(self) -> None:
        token = "a" * 64
        expected = hashlib.sha256(token.encode()).hexdigest()[:8]
        with patch("routes.auth.sdd_context", _mock_ctx(token=token)):
            client = TestClient(_make_app())
            response = client.get("/server-info")
        data = response.json()
        assert data["tokenHash"] == expected
        assert data["tokenHash"] != token

    # CON-0085 G-03: tokenHash is exactly 8 hex characters
    def test_token_hash_length_is_8(self) -> None:
        token = "deadbeef" * 8
        with patch("routes.auth.sdd_context", _mock_ctx(token=token)):
            client = TestClient(_make_app())
            response = client.get("/server-info")
        data = response.json()
        assert len(data["tokenHash"]) == 8

    # CON-0085 G-04: empty tokenHash when no token configured
    def test_empty_hash_when_no_token(self) -> None:
        with patch("routes.auth.sdd_context", _mock_ctx(token="")):
            client = TestClient(_make_app())
            response = client.get("/server-info")
        data = response.json()
        assert data["tokenHash"] == ""

    # CON-0085: name comes from project.name in config
    def test_name_from_config(self) -> None:
        with patch("routes.auth.sdd_context", _mock_ctx(name="My SDD Project")):
            client = TestClient(_make_app())
            response = client.get("/server-info")
        data = response.json()
        assert data["name"] == "My SDD Project"
