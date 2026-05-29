---
id: TST-0127
spec: SPEC-0028
contract: CON-0109
title: JobManager Unit-Tests
level: unit
status: implemented
artifact: tests/unit/test_pipeline_jobs.py
---

# Test: JobManager Unit-Tests

## Was wird geprüft

JobManager schreibt, liest und aktualisiert `.sdd/pipeline/{spec_id}-job.json` korrekt.

## Testfälle

| ID | Beschreibung | Erwartet |
|----|-------------|---------|
| TC-01 | `start()` legt job.json an | Datei existiert, status=running |
| TC-02 | `get()` liest zurück was `start()` schrieb | spec_id, status korrekt |
| TC-03 | `append()` häuft output-Zeilen auf | beide Zeilen im output |
| TC-04 | `finish(ok=True)` setzt status=done | finished_at gesetzt, result gespeichert |
| TC-05 | `finish(ok=False)` setzt status=failed | status=failed |
| TC-06 | `get()` für unbekannte Spec gibt None zurück | None |
