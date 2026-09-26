---
id: CON-0063
title: "sdd-implement-skill-flow"
type: behavior
format: gherkin
spec: SPEC-0020
version: 0.1.0
status: deprecated
artifact: ""
tests: [TST-0072]
deprecated_reason: "/sdd-implement läuft über sdd pipeline run (SPEC-0062, CON-0216)"
---

# Contract: /sdd-implement – Skill-Flow

> **Spec:** SPEC-0020 · **Typ:** Verhalten (Gherkin) · **Status:** draft

## Zweck

Beschreibt den vollständigen Ablauf des `/sdd-implement SPEC-XXXX`-Skill-Aufrufs.

## Garantien

- G-01: Skill prüft `status: in-progress` vor der Implementierung
- G-02: Holdout-Verzeichnis (`.sdd/holdout/`) wird nie gelesen
- G-03: Nach grünen Tests wird `sdd validate` ausgeführt
- G-04: Kein automatischer Git-Commit nach der Implementierung
