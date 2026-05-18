---
id: TST-0105
project: PRJ-0001
title: "Tests: /ws/chat Auth + Streaming-Format (CON-0074)"
contract: CON-0074
contracts: ["CON-0074"]
spec: SPEC-0023
level: contract
status: draft
artifact: "tests/unit/test_tst_0105.py"
---

# Test: WebSocket /ws/chat Auth + Streaming

> **Contract:** CON-0074 · **Typ:** Contract-Test · **Status:** draft

## Abgedeckte Garantien

- G-01: Fehlende Auth → WS close code 4001
- G-02: Eingehend: `{"text": "..."}` — andere Strukturen werden ignoriert
- G-03: Streaming-Token: `{"delta": "..."}`
- G-04: Command-Output-Frame: `{"type": "command_output", "line": "..."}`
- G-05: Abschluss-Frame: `{"type": "done"}`
- G-06: IntentParser läuft vor Claude
