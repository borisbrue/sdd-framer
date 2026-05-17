# TST-0097 – CON-0087: GET /api/auth/qr-payload (QR Onboarding Flow, server-side)
# Contract: CON-0087
# Spec: SPEC-0025
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from routes.auth import router


def _make_app() -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    return app


def _mock_ctx(*, name: str = "TestProject", external_url: str = "http://host:8000", token: str = "tok" * 21 + "x") -> MagicMock:
    ctx = MagicMock()
    config = MagicMock()
    config.raw = {"project": {"name": name}, "pwa": {"auth": {"token": token}}}
    ctx.get_config.return_value = config
    ctx.get_external_url.return_value = external_url
    return ctx


class TestTST0097:
    # CON-0087: returns {sdd, name, url, token} when fully configured
    def test_full_payload_when_configured(self) -> None:
        with patch("routes.auth.sdd_context", _mock_ctx()):
            client = TestClient(_make_app())
            response = client.get("/auth/qr-payload")
        assert response.status_code == 200
        data = response.json()
        assert data["sdd"] == 1
        assert "name" in data
        assert "url" in data
        assert "token" in data

    # CON-0087: token in payload is the full token, not the hash
    def test_payload_contains_full_token(self) -> None:
        full_token = "f" * 64
        with patch("routes.auth.sdd_context", _mock_ctx(token=full_token)):
            client = TestClient(_make_app())
            response = client.get("/auth/qr-payload")
        data = response.json()
        assert data["token"] == full_token
        assert len(data["token"]) == 64

    # CON-0087: returns 404 when no token configured
    def test_404_when_no_token(self) -> None:
        with patch("routes.auth.sdd_context", _mock_ctx(token="")):
            client = TestClient(_make_app())
            response = client.get("/auth/qr-payload")
        assert response.status_code == 404
        assert response.json()["detail"] == "no_token_configured"

    # CON-0087: returns 404 when no external_url configured
    def test_404_when_no_external_url(self) -> None:
        with patch("routes.auth.sdd_context", _mock_ctx(external_url="")):
            client = TestClient(_make_app())
            response = client.get("/auth/qr-payload")
        assert response.status_code == 404
        assert response.json()["detail"] == "no_external_url_configured"

    # CON-0087: name in payload matches project name
    def test_payload_name_from_config(self) -> None:
        with patch("routes.auth.sdd_context", _mock_ctx(name="Mobile QR Project", external_url="http://x.y:8000")):
            client = TestClient(_make_app())
            response = client.get("/auth/qr-payload")
        data = response.json()
        assert data["name"] == "Mobile QR Project"
        assert data["url"] == "http://x.y:8000"
