# TST-0107 – CON-0076: POST /api/push/subscribe Dedup + 503 ohne VAPID
# Contract: CON-0076
# Spec: SPEC-0023

import pytest


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
        raise NotImplementedError

    # CON-0076 G-04: Fehlende VAPID-Keys → HTTP 503
    def test_missing_vapid_returns_503(self) -> None:
        raise NotImplementedError

    # CON-0076 G-05: Erfolgreiche Registrierung → HTTP 201 {"subscribed": true}
    def test_successful_subscribe_returns_201(self) -> None:
        raise NotImplementedError
