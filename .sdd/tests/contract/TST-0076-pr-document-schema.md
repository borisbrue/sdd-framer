---
id: TST-0076
project: PRJ-0001
title: "Tests: PR-Dokument Schema-Validierung"
contract: CON-0067
contracts: ["CON-0067"]
spec: SPEC-0021
level: contract
status: draft
artifact: "tests/contract/test_pr_document_schema.py"
---

# Test: PR-Dokument Schema

> **Contract:** CON-0067 · **Typ:** Contract-Test · **Status:** draft

## Abgedeckte Garantien

- CON-0067 G-01: Pflichtfelder vorhanden (spec_id, branch, created, test_result, merge_command)
- CON-0067 G-02: Dokument ist valides Markdown mit YAML-Frontmatter
- CON-0067 G-03: `merge_command` enthält konkreten Git-Befehl

## Test-Datei

`tests/contract/test_pr_document_schema.py`

## Testfälle

| ID | Szenario | Erwartetes Ergebnis |
|---|---|---|
| TC-01 | Vollständiges valides PR-Dokument | Schema-Validierung besteht |
| TC-02 | `spec_id` fehlt | Schema-Fehler |
| TC-03 | `test_result: passed` mit 0 Tests | Schema-Fehler (INV-02) |
| TC-04 | `branch` passt nicht zu `spec_id` | Schema-Fehler (INV-01) |
| TC-05 | `merge_command` enthält nicht den Branch-Namen | Schema-Fehler (INV-03) |
