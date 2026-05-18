---
id: TST-0070
title: "TDD-Zyklus-Enforcement"
level: contract
spec: SPEC-0019
contract: CON-0061
status: draft
framework: pytest
artifact: ""
tags: []
---

# Test: TDD-Zyklus-Enforcement (TST-0070)

> **Level:** contract · **Spec:** SPEC-0019 · **Contract:** CON-0061 · **Status:** draft

## Was wird geprüft?

Dass der Implementierungs-Skill Tests vor dem Code ausführt und erst bei grünen Tests zur nächsten Einheit übergeht.

## Verknüpfung mit Contract

Dieser Test prüft konkret folgende Punkte aus CON-0061:

- [ ] G-01: Tests werden vor der Implementierung ausgeführt
- [ ] G-02: Übergang zur nächsten Einheit erst nach grünen Tests
- [ ] G-03: Bei >3 Fehlschlägen ohne Fortschritt → Nutzerabfrage
