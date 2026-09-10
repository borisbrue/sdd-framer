# TST-0098 – CON-0088: PWA Projects Schema (server-side compatibility)
# Contract: CON-0088 — sdd_projects[] schema: {id, name, baseUrl, token, addedAt}
# Spec: SPEC-0025
from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from routes.auth import router


def _make_app() -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    return app


def _mock_ctx(*, token: str, external_url: str = "http://host.local:8000", name: str = "Dev") -> MagicMock:
    ctx = MagicMock()
    config = MagicMock()
    config.raw = {"project": {"name": name}, "pwa": {"auth": {"token": token}}}
    config.root = Path("/tmp")
    ctx.get_config.return_value = config
    ctx.get_external_url.return_value = external_url
    ctx.is_blacklisted.return_value = False
    ctx.blacklist_token.return_value = None
    ctx.reload_config.return_value = None
    return ctx


# Token fresh from secrets.token_hex(32) is exactly 64 lowercase hex chars
HEX64 = re.compile(r"^[0-9a-f]{64}$")


class TestTST0098:
    # CON-0088: token returned by rotate-token matches schema (64-char hex)
    def test_rotate_token_matches_schema_format(self) -> None:
        old = "0" * 64
        ctx = _mock_ctx(token=old)
        with patch("routes.auth.sdd_context", ctx), patch("routes.auth._store_token"):
            client = TestClient(_make_app())
            response = client.post(
                "/auth/rotate-token",
                headers={"Authorization": f"Bearer {old}"},
            )
        new_token = response.json()["token"]
        assert HEX64.match(new_token), f"Token '{new_token}' not 64 hex chars"

    # CON-0088: qr-payload provides baseUrl (url field) matching schema
    def test_qr_payload_provides_base_url(self) -> None:
        with patch("routes.auth.sdd_context", _mock_ctx(token="a" * 64, external_url="http://192.168.1.10:8000")):
            client = TestClient(_make_app())
            response = client.get("/auth/qr-payload")
        data = response.json()
        assert data["url"] == "http://192.168.1.10:8000"

    # CON-0088: qr-payload token is 64-char hex (schema-compatible)
    def test_qr_payload_token_is_schema_compatible(self) -> None:
        token = "b" * 64
        with patch("routes.auth.sdd_context", _mock_ctx(token=token)):
            client = TestClient(_make_app())
            response = client.get("/auth/qr-payload")
        assert HEX64.match(response.json()["token"])

    # CON-0088 / CON-0086 v0.2.0: rotate-token schreibt genau einen neuen Token
    # und nichts sonst. Frueher schrieb die Rotation die ganze config.yaml neu,
    # und der Test pruefte, dass project.name das ueberlebte. Seit #103 geht
    # der Token nach .sdd/config.local.yaml — config.yaml wird gar nicht mehr
    # angefasst (siehe test_lokale_config.py::TestTokenEndpunkte).
    def test_rotate_token_schreibt_genau_den_neuen_token(self) -> None:
        old = "c" * 64
        geschrieben: list[str] = []

        def capture(config, token):
            geschrieben.append(token)

        ctx = _mock_ctx(token=old, name="My Project")
        with patch("routes.auth.sdd_context", ctx):
            with patch("routes.auth._store_token", side_effect=capture):
                client = TestClient(_make_app())
                response = client.post(
                    "/auth/rotate-token",
                    headers={"Authorization": f"Bearer {old}"},
                )
        assert len(geschrieben) == 1
        assert geschrieben[0] == response.json()["token"]
        assert HEX64.match(geschrieben[0])

    # CON-0088: successive rotations each produce unique tokens
    def test_successive_rotations_produce_unique_tokens(self) -> None:
        old1 = "d" * 64
        blacklist: set[str] = set()
        ctx = _mock_ctx(token=old1)
        ctx.is_blacklisted.side_effect = lambda t: t in blacklist
        ctx.blacklist_token.side_effect = blacklist.add

        with patch("routes.auth.sdd_context", ctx), patch("routes.auth._store_token"):
            client = TestClient(_make_app())
            r1 = client.post(
                "/auth/rotate-token",
                headers={"Authorization": f"Bearer {old1}"},
            )
            assert r1.status_code == 200
            r2 = client.post(
                "/auth/rotate-token",
                headers={"Authorization": f"Bearer {old1}"},
            )
            # second call with old1 should fail (blacklisted)
            assert r2.status_code == 401

    # CON-0088: server-info tokenHash does not expose raw token (privacy)
    def test_server_info_hides_raw_token(self) -> None:
        token = "e" * 64
        ctx = _mock_ctx(token=token)
        with patch("routes.auth.sdd_context", ctx):
            client = TestClient(_make_app())
            response = client.get("/server-info")
        data = response.json()
        assert data.get("tokenHash") != token
        assert len(data.get("tokenHash", "")) == 8

    # CON-0088: sdd field in qr-payload is protocol version 1
    def test_qr_payload_sdd_field_is_version_1(self) -> None:
        with patch("routes.auth.sdd_context", _mock_ctx(token="f" * 64)):
            client = TestClient(_make_app())
            response = client.get("/auth/qr-payload")
        assert response.json()["sdd"] == 1

    # CON-0088: name field in qr-payload matches config project name
    def test_qr_payload_name_matches_config(self) -> None:
        with patch("routes.auth.sdd_context", _mock_ctx(token="0a" * 32, name="QR Project Alpha")):
            client = TestClient(_make_app())
            response = client.get("/auth/qr-payload")
        assert response.json()["name"] == "QR Project Alpha"
