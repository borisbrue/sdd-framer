---
id: TST-0067
project: PRJ-0001
title: "Tests: DismissalFilter – Kontext-Pruning"
contract: CON-0053
contracts: ["CON-0053"]
spec: SPEC-0016
level: contract
status: draft
artifact: "tests/unit/test_dismissal_filter.py"
---

# Test: DismissalFilter

> **Contract:** CON-0053 · **Typ:** Contract-Test · **Status:** draft

## Abgedeckte Garantien

- CON-0053: Dismissed Items werden aus Prompt gefiltert
- Idempotenz, Reaktivierung, unbekannte IDs werden ignoriert

## Test-Datei

`tests/unit/test_dismissal_filter.py`
