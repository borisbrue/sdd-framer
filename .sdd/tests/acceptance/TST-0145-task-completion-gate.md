---
id: TST-0145
project: ""
title: "Tests: Task-Completion-Gate – Testpflicht vor passed (CON-0124)"
contract: CON-0124
contracts: ["CON-0124"]
spec: SPEC-0034
level: acceptance
status: draft
artifact: "tests/unit/test_tst_0145.py"
---

# Test: Task-Completion-Gate (CON-0124)

> **Contract:** CON-0124 · **Typ:** Acceptance-Test · **Status:** draft

## Abgedeckte Garantien

- CON-0124 G-01: passed-Transition mit grünem Test
- CON-0124 G-02: passed-Transition mit fehlgeschlagenem Test → failed
- CON-0124 INV-01: mark_passed() ohne test_ids → TaskTestRequiredError
- CON-0124 INV-02: Alle Tests müssen grün sein (partial pass nicht erlaubt)
- CON-0124 INV-03: error_context enthält originale Fehlermeldung
- SPEC-0034 FR-03: Tasks persistieren in tasks.json
- SPEC-0034 FR-02: SSE run_started-Event enthält run_id, spec_id, timestamp
