---
id: CON-0060
title: "sdd-start-lifecycle"
type: behavior
format: gherkin
spec: SPEC-0019
version: 0.1.0
status: draft
artifact: ""
tests: [TST-0069]
---

# Contract: sdd start – Status-Transition

> **Spec:** SPEC-0019 · **Typ:** Verhalten (Gherkin) · **Status:** draft

## Zweck

Beschreibt den `sdd start SPEC-XXXX`-Befehl und die Transition von `approved` → `in-progress`.

## Garantien

- G-01: `sdd start SPEC-XXXX` setzt `status: in-progress` in der Spec-Datei
- G-02: Nur Specs mit `status: approved` können gestartet werden
- G-03: Der Gate-Status wird auf `execute-unlocked` geprüft vor dem Start
