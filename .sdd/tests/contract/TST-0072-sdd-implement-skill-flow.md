---
id: TST-0072
title: "/sdd-implement Skill-Flow"
level: contract
spec: SPEC-0020
contract: CON-0063
status: draft
framework: pytest
artifact: ""
tags: []
---

# Test: /sdd-implement Skill-Flow (TST-0072)

> **Level:** contract · **Spec:** SPEC-0020 · **Contract:** CON-0063 · **Status:** draft

## Was wird geprüft?

Den vollständigen Ablauf des `/sdd-implement SPEC-XXXX`-Skill-Aufrufs inkl. Vorbedingungsprüfung und Abschluss.

## Verknüpfung mit Contract

Dieser Test prüft konkret folgende Punkte aus CON-0063:

- [ ] G-01: Skill prüft `status: in-progress` vor der Implementierung
- [ ] G-02: Holdout-Verzeichnis wird nicht gelesen
- [ ] G-03: `sdd validate` wird nach grünen Tests ausgeführt
- [ ] G-04: Kein automatischer Git-Commit
