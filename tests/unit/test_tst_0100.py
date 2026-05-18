# TST-0100 – CON-0090: PWA ApiClient — Auth-Header + 401-Handler
# Contract: CON-0090
# Spec: SPEC-0024
# Generiert von 'sdd start' – TODO: implementieren nach SPEC-0023

import pytest


class TestTST0100:
    # CON-0090 G-01: Jeder HTTP-Request enthält Authorization: Bearer <token>
    def test_api_client_sets_auth_header(self) -> None:
        raise NotImplementedError

    # CON-0090 G-02: Bei HTTP 401 → Token löschen + ConnectionStore setup_required
    def test_api_client_handles_401(self) -> None:
        raise NotImplementedError

    # CON-0090 G-05: getSpecs() ruft GET /api/specs auf
    def test_get_specs_calls_correct_endpoint(self) -> None:
        raise NotImplementedError

    # CON-0090 G-08: Netzwerkfehler → ConnectionStore disconnected
    def test_network_error_sets_disconnected(self) -> None:
        raise NotImplementedError
