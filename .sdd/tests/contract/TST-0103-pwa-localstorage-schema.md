---
id: TST-0103
project: PRJ-0001
title: "Tests: PWA localStorage-Schema sdd_config (CON-0093)"
contract: CON-0093
contracts: ["CON-0093"]
spec: SPEC-0024
level: unit
status: draft
artifact: "tests/unit/test_tst_0103.py"
---

# Test: PWA localStorage-Schema

> **Contract:** CON-0093 · **Typ:** Unit-Test · **Status:** draft

## Abgedeckte Garantien

- CON-0093 G-01: baseUrl ist valide URL
- CON-0093 G-02: token ist nicht leer wenn sdd_config existiert
- CON-0093 G-05: Nach Setup enthält sdd_config mindestens baseUrl + token

## Hinweis

Client-seitiges localStorage — Python-Stubs. Vollständige Tests im
TypeScript-Teil (Vitest) nach SPEC-0024-Implementierung.
