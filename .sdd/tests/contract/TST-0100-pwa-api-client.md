---
id: TST-0100
project: PRJ-0001
title: "Tests: PWA ApiClient — Auth-Header + 401-Handler (CON-0090)"
contract: CON-0090
contracts: ["CON-0090"]
spec: SPEC-0024
level: unit
status: draft
artifact: "tests/unit/test_tst_0100.py"
---

# Test: PWA ApiClient

> **Contract:** CON-0090 · **Typ:** Unit-Test · **Status:** draft

## Abgedeckte Garantien

- CON-0090 G-01: Jeder HTTP-Request enthält `Authorization: Bearer <token>`
- CON-0090 G-02: Bei HTTP 401 → Token löschen, ConnectionStore → `setup_required`
- CON-0090 G-05: `getSpecs()` sendet GET zu `<baseUrl>/api/specs`
- CON-0090 G-08: Netzwerkfehler → ConnectionStore → `disconnected`

## Hinweis

Diese Tests prüfen den TypeScript-ApiClient (client-seitig).
Python-Stubs bis zur vollständigen SPEC-0023-Implementierung.
