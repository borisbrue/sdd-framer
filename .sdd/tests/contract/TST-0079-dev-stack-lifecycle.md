---
id: TST-0079
project: PRJ-0001
title: "Tests: Dev-Stack Lifecycle + Runtime-Auswahl (CON-0069)"
contract: CON-0069
contracts: ["CON-0069"]
spec: SPEC-0022
level: contract
status: draft
artifact: "tests/unit/test_tst_0079.py"
---

# Test: Dev-Stack Lifecycle

> **Contract:** CON-0069 · **Typ:** Contract-Test · **Status:** draft

## Abgedeckte Garantien

- CON-0069 G-01: `sdd dev build` delegiert an konfigurierte Runtime
- CON-0069 G-02: Alle `sdd dev`-Befehle nutzen ContainerRuntime-Interface
- CON-0069 G-03: `sdd dev push` ohne Registry → Fehler
- CON-0069 G-04: `sdd dev start` delegiert an `up` wenn compose_file konfiguriert
- CON-0069 G-05/G-06: `sdd dev up/down` startet/stoppt Compose-Stack
- CON-0069 G-07: Runtime-Umschaltung nur per config

## Test-Datei

`tests/unit/test_tst_0079.py`
