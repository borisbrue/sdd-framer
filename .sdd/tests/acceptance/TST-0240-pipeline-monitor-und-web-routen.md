---
id: TST-0240
title: "Pipeline-Monitor und Web-Routen"
level: acceptance
spec: SPEC-0058
contract: CON-0211
status: planned
framework: pytest
artifact: "tests/acceptance/test_con_0211.py"
tags: [pipeline, cleanup]
---

# Test: Pipeline-Monitor und Web-Routen

> **Level:** acceptance · **Spec:** SPEC-0058 · **Contract:** CON-0211 · **Status:** planned

## Was wird geprüft?

Leseschnittstelle `sdd_cli.pipeline.monitor` mit echten Run-Verzeichnissen; Monitor-Routen, `pipeline status --json` und Web-Routen mit Pipeline-Läufen gegen den Fake-LLM-Server.

## Verknüpfung mit Contract

- [x] INV-01
- [x] INV-02
- [x] INV-03
- [x] INV-04
- [x] INV-05
- [x] INV-06
- [x] INV-07
- [x] INV-08

## Verknüpfung mit Spec

FR-05, FR-06, FR-07, FR-08
