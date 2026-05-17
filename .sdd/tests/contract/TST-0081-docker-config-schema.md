---
id: TST-0081
project: PRJ-0001
title: "Tests: docker: Config-Schema (CON-0072)"
contract: CON-0072
contracts: ["CON-0072"]
spec: SPEC-0022
level: contract
status: draft
artifact: "tests/unit/test_tst_0081.py"
---

# Test: Docker Config Schema

> **Contract:** CON-0072 · **Typ:** Contract-Test · **Status:** draft

## Abgedeckte Garantien

- CON-0072 INV-01: Ungültige Runtime → Fehler
- CON-0072 INV-02: Minimale Config valide
- CON-0072 INV-03: max_lines Bereichsvalidierung

## Test-Datei

`tests/unit/test_tst_0081.py`
