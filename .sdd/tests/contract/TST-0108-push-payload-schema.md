---
id: TST-0108
project: PRJ-0001
title: "Tests: Push-Notification-Payload Schema (CON-0077)"
contract: CON-0077
contracts: ["CON-0077"]
spec: SPEC-0023
level: contract
status: draft
artifact: "tests/unit/test_tst_0108.py"
---

# Test: Push-Notification-Payload Schema

> **Contract:** CON-0077 · **Typ:** Contract-Test · **Status:** draft

## Abgedeckte Garantien

- G-01: `type` ist immer einer der vier definierten Werte
- G-02: `spec_id` entspricht dem Format `SPEC-XXXX` (4 Ziffern)
- G-03: `message` ist niemals leer
- G-04: JSON-Größe ≤ 4096 Bytes
- G-05: Payload-Encoding: UTF-8 JSON-String
- Trigger-Mapping: orchestrate→orchestrate_done, dev build→build_done, exit≠0→build_failed
