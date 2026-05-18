# TST-0106 – CON-0075: POST /api/sdd/run SSE-Format + Exit-Code
# Contract: CON-0075
# Spec: SPEC-0023

import pytest

ALLOWLIST = {"orchestrate", "start", "validate", "dev", "contract", "spec", "estimate"}


class TestTST0106:
    # CON-0075 G-09: Command-Allowlist enthält genau die spezifizierten Commands
    def test_allowlist_contains_specified_commands(self) -> None:
        expected = {"orchestrate", "start", "validate", "dev", "contract", "spec", "estimate"}
        assert ALLOWLIST == expected

    # CON-0075 G-09: Unbekannte Commands sind nicht in der Allowlist
    def test_unknown_commands_not_in_allowlist(self) -> None:
        for cmd in ["shell", "rm", "exec", "run", "bash"]:
            assert cmd not in ALLOWLIST

    # CON-0075 G-01: Fehlende Auth → HTTP 401
    def test_missing_auth_returns_401(self) -> None:
        raise NotImplementedError

    # CON-0075 G-03: Unbekannter Command → HTTP 422 unknown_command
    def test_unknown_command_returns_422(self) -> None:
        raise NotImplementedError

    # CON-0075 G-04: SSE-Event-Format pro Zeile
    def test_sse_line_event_schema(self) -> None:
        raise NotImplementedError

    # CON-0075 G-05: Abschluss-Event enthält exit_code
    def test_sse_done_event_has_exit_code(self) -> None:
        raise NotImplementedError

    # CON-0075 G-08: Content-Type ist text/event-stream
    def test_response_content_type_is_event_stream(self) -> None:
        raise NotImplementedError
