---
id: TST-0128
spec: SPEC-0028
contract: CON-0108
title: Interactive API KI-Aktionen Unit-Tests
level: unit
status: implemented
artifact: tests/unit/test_interactive_routes.py
---

# Test: Interactive API KI-Aktionen Unit-Tests

## Was wird geprüft

review_spec, propose_contracts und generate_holdouts liefern korrekte Responses und halten die Constraints ein (Holdout-Isolation, Gate-Phase-Markierung).

## Testfälle

| ID | FR | Beschreibung | Erwartet |
|----|----|-------------|---------|
| TC-01 | FR-01 | review_spec: LLM antwortet korrekt | ok=True, Review-Datei existiert |
| TC-02 | FR-01 | review_spec: Spec nicht gefunden | HTTP 404 |
| TC-03 | FR-01 | review_spec: LLM-Fehler | ok=False, Fehlermeldung in output |
| TC-04 | FR-02 | propose_contracts: schreibt Contract-Dateien | ok=True, Dateien vorhanden |
| TC-05 | FR-02 | propose_contracts: verknüpft CON-ID in Spec | Frontmatter enthält CON-ID |
| TC-06 | FR-05 | generate_holdouts: keine Contracts → ok=False | output nennt Contracts |
| TC-07 | FR-05 | generate_holdouts: nur Contract-Kontext im Prompt | kein "tool/" im LLM-Prompt |
