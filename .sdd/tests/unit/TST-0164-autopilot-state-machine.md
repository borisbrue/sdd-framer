---
id: TST-0164
project: ""
title: "AutopilotStateMachine — Transitionen, Iterationszähler, Fortschritts-Check"
level: unit
spec: SPEC-0037
contract: CON-0143
status: implemented
framework: pytest
artifact: "tests/unit/test_tst_0164.py"
tags: []
---

# Test: AutopilotStateMachine

> **Level:** unit · **Spec:** SPEC-0037 · **Contract:** CON-0143 · **Status:** implemented

## Was wird geprüft?

Ob `AutopilotStateMachine` alle Zustandsübergänge korrekt durchführt, den
Iterationszähler inkrementiert, bei Stagnation eskaliert und das Gate bei
`automated_gate_approval: false` blockiert (CON-0143 INV-01–INV-05).

## Verknüpfung mit Contract

- [x] INV-01: Transitionen deterministisch
- [x] INV-02: fix_loop inkrementiert iteration_count, Eskalation bei max
- [x] INV-03: Fortschritts-Check erkennt verbesserte Tests
- [x] INV-05: automated_gate_approval: false → Gate blockiert
