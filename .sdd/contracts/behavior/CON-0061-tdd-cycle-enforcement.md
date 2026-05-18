---
id: CON-0061
title: "tdd-cycle-enforcement"
type: behavior
format: gherkin
spec: SPEC-0019
version: 0.1.0
status: draft
artifact: ""
tests: [TST-0070]
---

# Contract: TDD-Zyklus-Enforcement

> **Spec:** SPEC-0019 · **Typ:** Verhalten (Gherkin) · **Status:** draft

## Zweck

Stellt sicher, dass der Implementierungs-Skill den TDD-Zyklus (Red → Green → Refactor) einhält.

## Garantien

- G-01: Tests werden vor dem Implementierungscode ausgeführt (Red-Phase)
- G-02: Erst nach grünen Tests wird zur nächsten Einheit übergegangen
- G-03: Bei >3 Fehlschlägen ohne Fortschritt wird der Nutzer gefragt
