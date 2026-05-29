---
id: CON-0057
title: "sdd-skill-commands"
type: behavior
format: gherkin
spec: SPEC-0020
version: 0.1.0
status: draft
artifact: ""
tests: [TST-0063]
---

# Contract: SDD Skill – /sdd Slash-Commands

> **Spec:** SPEC-0018 · **Typ:** Verhalten (Gherkin) · **Status:** draft

## Zweck

Definiert das Verhalten der `/sdd`-Slash-Commands in Claude Code für den geführten Spec-Zyklus.

## Garantien

- G-01: `/sdd-new spec` startet die interaktive Spec-Erstellung
- G-02: `/sdd-implement SPEC-XXXX` startet die TDD-Implementierungsphase
- G-03: Ungültige SPEC-IDs werden mit einer klaren Fehlermeldung abgewiesen
