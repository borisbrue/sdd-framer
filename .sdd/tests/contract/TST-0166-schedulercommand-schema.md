---
id: TST-0166
project: ""
title: "SchedulerCommand-Schema — Pflichtfelder, unbekannte Commands → 422"
level: contract
spec: SPEC-0037
contract: CON-0142
status: implemented
framework: pytest
artifact: "tests/contract/test_tst_0166.py"
tags: []
---

# Test: SchedulerCommand-Schema

> **Level:** contract · **Spec:** SPEC-0037 · **Contract:** CON-0142 · **Status:** implemented

## Was wird geprüft?

Ob `POST /orchestrate/command/{run_id}` Pflichtfelder korrekt validiert,
unbekannte Command-Typen mit 422 ablehnt und `restart_task` nur für
`failed`-Tasks akzeptiert (CON-0142 INV-03–INV-04).

## Verknüpfung mit Contract

- [x] INV-03: restart_task nur für status=failed
- [x] INV-04: Unbekannte Command-Typen → HTTP 422
