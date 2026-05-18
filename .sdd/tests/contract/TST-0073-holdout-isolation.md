---
id: TST-0073
title: "Holdout-Isolation"
level: contract
spec: SPEC-0020
contract: CON-0064
status: draft
framework: pytest
artifact: ""
tags: []
---

# Test: Holdout-Isolation (TST-0073)

> **Level:** contract · **Spec:** SPEC-0020 · **Contract:** CON-0064 · **Status:** draft

## Was wird geprüft?

Dass das Holdout-Verzeichnis (`.sdd/holdout/`) vom Implementierungs-Skill vollständig isoliert ist.

## Verknüpfung mit Contract

Dieser Test prüft konkret folgende Punkte aus CON-0064:

- [ ] G-01: `.sdd/holdout/` wird vom Implementierungs-Skill nicht gelesen
- [ ] G-02: Evaluator-Szenarien werden erst nach der Implementierung ausgeführt
- [ ] G-03: Dark Factory Pattern — Implementierung und Evaluation in separaten Phasen
