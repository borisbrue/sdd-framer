# TST-0107 – CON-0076: POST /api/push/subscribe Dedup + 503 ohne VAPID
# Contract: CON-0076
# Spec: SPEC-0023

from __future__ import annotations

from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from routes.remote import router


class PushStoreMock:
    def __init__(self) -> None:
        self._subscriptions: dict[str, dict] = {}

    def subscribe(self, sub: dict) -> bool:
        endpoint = sub["endpoint"]
        already = endpoint in self._subscriptions
        self._subscriptions[endpoint] = sub
        return not already

    def count(self) -> int:
        return len(self._subscriptions)


def _make_app() -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    return app


def _mock_ctx(token="tok", has_vapid=True):
    ctx = MagicMock()
    vapid = {"private_key": "key", "claims_email": "mailto:test@test.com"} if has_vapid else {}
    ctx.get_config.return_value.raw = {
        "pwa": {"auth": {"token": token}, "vapid": vapid}
    }
    ctx.is_blacklisted.return_value = False
    return ctx


class TestTST0107:
    # CON-0076 G-03: Gleicher endpoint → keine Duplikate im PushStore
    def test_duplicate_endpoint_deduplicated(self) -> None:
        store = PushStoreMock()
        sub = {"endpoint": "https://fcm.example.com/xyz", "keys": {"p256dh": "abc", "auth": "def"}}
        store.subscribe(sub)
        store.subscribe(sub)
        assert store.count() == 1

    # CON-0076 G-03: Unterschiedliche endpoints → beide gespeichert
    def test_different_endpoints_both_stored(self) -> None:
        store = PushStoreMock()
        sub_a = {"endpoint": "https://fcm.example.com/aaa", "keys": {"p256dh": "x", "auth": "y"}}
        sub_b = {"endpoint": "https://fcm.example.com/bbb", "keys": {"p256dh": "x", "auth": "y"}}
        store.subscribe(sub_a)
        store.subscribe(sub_b)
        assert store.count() == 2

    # CON-0076 G-01: Fehlende Auth → HTTP 401
    def test_missing_auth_returns_401(self) -> None:
        with patch("routes.remote.sdd_context", _mock_ctx()):
            client = TestClient(_make_app(), raise_server_exceptions=False)
            response = client.post(
                "/push/subscribe",
                json={"endpoint": "https://fcm.example.com/x", "keys": {"p256dh": "a", "auth": "b"}},
            )
        assert response.status_code == 401

    # CON-0076 G-04: Fehlende VAPID-Keys → HTTP 503
    def test_missing_vapid_returns_503(self) -> None:
        ctx = _mock_ctx(token="tok", has_vapid=False)
        with patch("routes.remote.sdd_context", ctx):
            client = TestClient(_make_app(), raise_server_exceptions=False)
            response = client.post(
                "/push/subscribe",
                json={"endpoint": "https://fcm.example.com/x", "keys": {"p256dh": "a", "auth": "b"}},
                headers={"Authorization": "Bearer tok"},
            )
        assert response.status_code == 503
        assert response.json()["detail"] == "vapid_not_configured"

    # CON-0076 G-05: Erfolgreiche Registrierung → HTTP 201 {"subscribed": true}
    def test_successful_subscribe_returns_201(self) -> None:
        ctx = _mock_ctx(token="tok", has_vapid=True)
        with patch("routes.remote.sdd_context", ctx):
            client = TestClient(_make_app())
            response = client.post(
                "/push/subscribe",
                json={"endpoint": "https://fcm.example.com/abc", "keys": {"p256dh": "a", "auth": "b"}},
                headers={"Authorization": "Bearer tok"},
            )
        assert response.status_code == 201
        assert response.json() == {"subscribed": True}
