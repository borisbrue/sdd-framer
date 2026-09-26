---
id: TST-0244
title: "Verweise, Entfernen, Config-Migration und ARCH-05"
level: acceptance
spec: SPEC-0062
contract: CON-0215
status: planned
framework: pytest
artifact: "tests/acceptance/test_con_0215.py"
tags: [pipeline]
---

# Test: Verweise, Entfernen, Config-Migration und ARCH-05

> **Level:** acceptance · **Spec:** SPEC-0062 · **Contract:** CON-0215 · **Status:** planned

## Was wird geprüft?

Die vier Verweise (Exit 1, Ersatz mit IDs, keine Nebenwirkungen, nicht in der Hilfe), das Fehlen der entfernten Module, die Config-Migration in allen Varianten (mit/ohne Routing, ohne lokales Modell, Konflikt, idempotent), den Lifecycle-Status der abgelösten Artefakte und ARCH-05 an einem Fixture-Projekt und am Repository.

## Vorbedingungen

- Temporäres SDD-Projekt über `sdd init`; LLM-Rollen gegen den Fake-LLM-Server aus `tests/`.
- Kein echter `claude`-, `gh`- oder Netzwerkaufruf.

## Verknüpfung mit Contract

Dieser Test prüft konkret folgende Punkte aus CON-0215:

- [ ] INV-01
- [ ] INV-02
- [ ] INV-03
- [ ] INV-04
- [ ] INV-05
- [ ] INV-06
- [ ] INV-07
