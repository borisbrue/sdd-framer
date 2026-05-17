---
id: TST-0075
project: PRJ-0001
title: "Tests: sdd pr – Validierungsgatter"
contract: CON-0066
contracts: ["CON-0066"]
spec: SPEC-0021
level: contract
status: draft
artifact: "tests/contract/test_sdd_pr_gate.py"
---

# Test: sdd pr Validierungsgatter

> **Contract:** CON-0066 · **Typ:** Contract-Test · **Status:** draft

## Abgedeckte Garantien

- CON-0066 G-01: Gate blockiert bei fehlgeschlagenen Tests
- CON-0066 G-02: Gate blockiert bei `sdd validate`-Fehlern
- CON-0066 G-03: Warnung (kein Abbruch) bei uncommitted changes
- CON-0066 G-04: PR-Dokument wird bei grünem Gate erstellt
- CON-0066 G-05: Regression-Check ist Teil des PR-Dokuments

## Test-Datei

`tests/contract/test_sdd_pr_gate.py`

## Testfälle

| ID | Szenario | Erwartetes Ergebnis |
|---|---|---|
| TC-01 | Tests grün + validate sauber | PR-Dokument erstellt, Merge-Anleitung ausgegeben |
| TC-02 | Tests fehlgeschlagen | Gate blockiert, kein PR-Dokument |
| TC-03 | `sdd validate` Fehler | Gate blockiert, Fehler ausgegeben |
| TC-04 | Uncommitted changes | Warnung, Gate fährt fort, PR-Dokument erstellt |
| TC-05 | Kein Test-Ergebnis vorhanden | Gate blockiert mit Hinweis |
