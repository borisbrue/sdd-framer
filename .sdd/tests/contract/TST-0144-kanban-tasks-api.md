---
id: TST-0144
project: ""
title: "Tests: Kanban Tasks API – GET /tasks Schema (CON-0123)"
contract: CON-0123
contracts: ["CON-0123"]
spec: SPEC-0034
level: contract
status: draft
artifact: "tests/unit/test_tst_0144.py"
---

# Test: Kanban Tasks API (CON-0123)

> **Contract:** CON-0123 · **Typ:** Contract-Test · **Status:** draft

## Abgedeckte Garantien

- CON-0123 G-01: Task-Objekt-Schema vollständig (alle Pflichtfelder vorhanden)
- CON-0123 INV-01: estimated_tokens > 0
- CON-0123 INV-02: actual_tokens ist null solange Task nicht committed/failed
- CON-0123 INV-04: Leere Task-Liste wenn kein Run vorhanden (kein 404)
- CON-0123 INV-05: Immer neuester Run zurückgegeben
- CON-0123 INV-08: task_update-Event enthält run_id und timestamp
