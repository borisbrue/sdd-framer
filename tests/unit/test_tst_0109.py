# TST-0109 – CON-0078: Remote API SLO
# Contract: CON-0078
# Spec: SPEC-0023
# Stubs — implementieren nach SPEC-0023 Backend (ChatService, SddRunService, PushStore)

import pytest


class TestTST0109:
    # CON-0078: /ws/chat first-token p95 < 200ms (LLM gemockt, 10 Messungen)
    def test_ws_chat_first_token_p95_under_200ms(self) -> None:
        raise NotImplementedError

    # CON-0078: /api/sdd/run first SSE-Zeile p95 < 1000ms (subprocess gemockt, 10 Messungen)
    def test_sdd_run_first_sse_line_p95_under_1000ms(self) -> None:
        raise NotImplementedError

    # CON-0078: /api/push/subscribe Response p95 < 100ms (20 Messungen)
    def test_push_subscribe_p95_under_100ms(self) -> None:
        raise NotImplementedError
