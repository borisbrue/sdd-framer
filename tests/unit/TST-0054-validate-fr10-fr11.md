---
id: TST-0054
project: PRJ-0001
title: "validate – ERROR für Contract(review) ohne Test (FR-10) und WARNING für Spec(approved)+Contract(review) (FR-11)"
level: unit
spec: SPEC-0010
contract: CON-0040
status: draft
framework: pytest
artifact: "tests/unit/test_lifecycle.py"
tags: ["lifecycle", "validate", "fr-10", "fr-11"]
---

# Test: validate Lifecycle-Regeln FR-10 und FR-11

Unit-Tests für `_check_lifecycle_rules()` in `validate.py`.

## Test Cases

| TC    | Beschreibung                                                                     | Erwartet                                             |
|-------|----------------------------------------------------------------------------------|------------------------------------------------------|
| TC-01 | Contract mit `status: review` und `tests: []` → validate liefert ERROR          | Issue(severity=error) mit FR-10-Meldung              |
| TC-02 | Contract mit `status: review` und `tests: ["TST-0001"]` → kein FR-10-Fehler     | Keine FR-10-Issues                                   |
| TC-03 | Contract mit `status: draft` und `tests: []` → kein FR-10-Fehler                | Keine FR-10-Issues                                   |
| TC-04 | Spec `approved` + referenzierter Contract `review` → validate liefert WARNING   | Issue(severity=warning) mit FR-11-Meldung            |
| TC-05 | Spec `approved` + alle Contracts `approved` → kein FR-11-Warning                | Keine FR-11-Issues                                   |
