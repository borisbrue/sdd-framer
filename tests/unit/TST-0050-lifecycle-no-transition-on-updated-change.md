---
id: TST-0050
project: PRJ-0001
title: "lifecycle – Kein Übergang bei reiner updated:-Änderung"
level: unit
spec: SPEC-0010
contract: CON-0037
status: draft
framework: pytest
artifact: "tests/unit/test_lifecycle.py"
tags: ["lifecycle", "status-transition", "idempotency"]
---

# Test: Kein falscher Statusübergang

Unit-Tests für Idempotenz von `compute_content_hash()`.

## Test Cases

| TC    | Beschreibung                                                              | Erwartet                         |
|-------|---------------------------------------------------------------------------|----------------------------------|
| TC-01 | Nur `updated:`-Zeile geändert → check_transitions gibt leere Liste zurück | Keine StatusChange               |
| TC-02 | Nur `status:`-Zeile geändert → kein Übergang                              | Keine StatusChange               |
| TC-03 | status-check auf Erstlauf (keine hashes.json) → kein Übergang, Init       | Leere Liste, Datei wird angelegt |
