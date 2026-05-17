---
id: TST-0082
project: PRJ-0001
title: "Tests: WebSocket /ws/logs/{spec_id} (CON-0071)"
contract: CON-0071
contracts: ["CON-0071"]
spec: SPEC-0022
level: contract
status: draft
artifact: "tests/unit/test_tst_0082.py"
---

# Test: WebSocket Logs Endpoint

> **Contract:** CON-0071 · **Typ:** Contract-Test · **Status:** draft

## Abgedeckte Garantien

- CON-0071 G-02: JSON-Nachrichtenformat
- CON-0071 G-03: Buffer-History mit `buffered: true`
- CON-0071 G-04: Fehlermeldung bei inaktivem Stream
- CON-0071 INV-01: spec_id-Format-Validierung

## Test-Datei

`tests/unit/test_tst_0082.py`
