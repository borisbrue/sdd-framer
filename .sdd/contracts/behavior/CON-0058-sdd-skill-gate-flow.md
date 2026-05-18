---
id: CON-0058
title: "sdd-skill-gate-flow"
type: behavior
format: gherkin
spec: SPEC-0018
version: 0.1.0
status: draft
artifact: ""
tests: [TST-0064]
---

# Contract: SDD Skill – Gate-Flow-Integration

> **Spec:** SPEC-0018 · **Typ:** Verhalten (Gherkin) · **Status:** draft

## Zweck

Beschreibt, wie der SDD-Skill den Gate-Flow (spec-review, contracts-proposed, etc.) führt.

## Garantien

- G-01: Der Skill liest den aktuellen Gate-Status aus `.sdd/pipeline/SPEC-XXXX-gate.json`
- G-02: Jede Phase wird sequentiell ausgeführt und im Gate-JSON protokolliert
- G-03: Bei fehlgeschlagener Phase bricht der Skill ab und meldet den Fehler
