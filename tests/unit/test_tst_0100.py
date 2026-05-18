# TST-0100 – CON-0090: PWA ApiClient — Auth-Header + 401-Handler
# Contract: CON-0090 | Spec: SPEC-0024
# Implementiert als Deno-Tests: web/pwa/src/__tests__/tst_0100.test.ts
# Ausführen: cd web/pwa && deno test --no-check --unstable-sloppy-imports --allow-read --allow-env src/__tests__/

import pytest


class TestTST0100:
    def test_api_client_sets_auth_header(self) -> None:
        pytest.skip("client-side TypeScript — see web/pwa/src/__tests__/tst_0100.test.ts")

    def test_api_client_handles_401(self) -> None:
        pytest.skip("client-side TypeScript — see web/pwa/src/__tests__/tst_0100.test.ts")

    def test_get_specs_calls_correct_endpoint(self) -> None:
        pytest.skip("client-side TypeScript — see web/pwa/src/__tests__/tst_0100.test.ts")

    def test_network_error_sets_disconnected(self) -> None:
        pytest.skip("client-side TypeScript — see web/pwa/src/__tests__/tst_0100.test.ts")
