---
id: TST-0101
project: PRJ-0001
title: "Tests: PWA Setup-Flow — GET /api/specs Validierung (CON-0091)"
contract: CON-0091
contracts: ["CON-0091"]
spec: SPEC-0024
level: contract
status: draft
artifact: "tests/unit/test_tst_0101.py"
---

# Test: PWA Setup-Flow

> **Contract:** CON-0091 · **Typ:** Contract-Test · **Status:** draft

## Abgedeckte Garantien

- CON-0091: GET /api/specs gibt HTTP 200 + korrekte Felder zurück (Setup-Validierung)
- CON-0091 INV-01: Endpoint liefert die erwarteten Felder für Setup-Flow-Validierung
- CON-0091: Response ist eine Liste (Array) von Spec-Objekten
