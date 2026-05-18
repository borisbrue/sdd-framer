---
id: CON-0064
title: "holdout-isolation"
type: behavior
format: gherkin
spec: SPEC-0020
version: 0.1.0
status: draft
artifact: ""
tests: [TST-0073]
---

# Contract: Holdout-Isolation

> **Spec:** SPEC-0020 · **Typ:** Verhalten (Gherkin) · **Status:** draft

## Zweck

Sichert die vollständige Isolation des Evaluators von Implementierungsdetails durch das Holdout-Verzeichnis.

## Garantien

- G-01: `.sdd/holdout/` wird vom Implementierungs-Skill nicht gelesen
- G-02: Evaluator-Szenarien in `.sdd/holdout/` werden erst nach der Implementierung ausgeführt
- G-03: Implementierungscode und Holdout-Tests sind in separaten Phasen (Dark Factory Pattern)
