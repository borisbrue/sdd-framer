# TST-0105 – CON-0074: /ws/chat Auth + Streaming-Format
# Contract: CON-0074
# Spec: SPEC-0023
# Stubs — implementieren nach SPEC-0023 Backend (ChatService + IntentParser)

import pytest


class TestTST0105:
    # CON-0074 G-01: Fehlende Auth → WS close code 4001
    def test_missing_auth_closes_with_4001(self) -> None:
        raise NotImplementedError

    # CON-0074 G-01: Falscher Token → WS close code 4001
    def test_wrong_token_closes_with_4001(self) -> None:
        raise NotImplementedError

    # CON-0074 G-03: Streaming-Token hat delta-Feld
    def test_streaming_token_has_delta_field(self) -> None:
        raise NotImplementedError

    # CON-0074 G-04: Command-Output-Frame hat type + line
    def test_command_output_frame_schema(self) -> None:
        raise NotImplementedError

    # CON-0074 G-05: Abschluss-Frame hat type=done
    def test_done_frame_closes_response(self) -> None:
        raise NotImplementedError

    # CON-0074 G-06: IntentParser läuft vor Claude (Command-Output vor Delta)
    def test_intent_triggers_command_before_claude(self) -> None:
        raise NotImplementedError
