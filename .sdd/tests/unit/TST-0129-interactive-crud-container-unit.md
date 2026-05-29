---
id: TST-0129
spec: SPEC-0028
contract: CON-0110
title: Interactive API CRUD + Container Unit-Tests
level: unit
status: implemented
artifact: tests/unit/test_interactive_routes.py
---

# Test: Interactive API CRUD + Container Unit-Tests

## Was wird geprüft

Contract/Holdout-Lesen und -Schreiben, run_tests_in_container Verhalten, Job-Polling.

## Testfälle

| ID | FR | Beschreibung | Erwartet |
|----|----|-------------|---------|
| TC-08 | FR-06 | get_contract: gibt body + frontmatter zurück | id, body, frontmatter vorhanden |
| TC-09 | FR-06 | put_contract: überschreibt body | Neuer Inhalt nach erneutem GET |
| TC-10 | FR-07 | get_holdout: gibt body + frontmatter zurück | id, body vorhanden |
| TC-11 | FR-07 | put_holdout: überschreibt body | ok=True |
| TC-12 | FR-09 | run_tests: Container nicht gestartet | ok=False, "läuft nicht" |
| TC-13 | FR-09 | run_tests: rc=0 → ok=True | output enthält pytest-Ausgabe |
| TC-14 | FR-09 | run_tests: rc!=0 → ok=False | output enthält FAILED |
| TC-15 | FR-11 | get_job: kein Job → status=idle | status="idle" |
| TC-16 | FR-11 | get_job: laufender Job | status="running", command korrekt |
