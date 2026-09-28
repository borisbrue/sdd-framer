---
id: TST-0259
title: "S3-Abnahme mit Task-Fakten"
level: acceptance
spec: SPEC-0064
contract: CON-0230
status: planned
framework: pytest
artifact: "tests/acceptance/test_con_0230.py"
tags: [pipeline, supervisor]
---

# Test: S3-Abnahme mit Task-Fakten

> **Level:** acceptance · **Spec:** SPEC-0064 · **Contract:** CON-0230 · **Status:** planned

## Was wird geprüft?

Schnappschuss `approved-tasks.json` bei S1, Aufbau von `facts.tasks` und `facts.frs[].tasks` an S3, Halt
ohne Schnappschuss, `reopen` mit Task-IDs aus den Fakten, Anleitung und Golden Cases.

## Verknüpfung mit Contract

Alle Invarianten und Szenarien aus CON-0230; Schemaprüfung der Anfragen gegen CON-0202.
