---
id: TST-0069
title: "sdd start – Status-Transition"
level: contract
spec: SPEC-0019
contract: CON-0060
status: draft
framework: pytest
artifact: ""
tags: []
---

# Test: sdd start – Status-Transition (TST-0069)

> **Level:** contract · **Spec:** SPEC-0019 · **Contract:** CON-0060 · **Status:** draft

## Was wird geprüft?

Dass `sdd start SPEC-XXXX` den Spec-Status von `approved` auf `in-progress` setzt und nur für `approved`-Specs funktioniert.

## Verknüpfung mit Contract

Dieser Test prüft konkret folgende Punkte aus CON-0060:

- [ ] G-01: `sdd start SPEC-XXXX` setzt `status: in-progress`
- [ ] G-02: Nur `approved`-Specs können gestartet werden
- [ ] G-03: Gate-Status wird auf `execute-unlocked` geprüft
