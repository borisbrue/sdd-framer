---
id: TST-0049
project: PRJ-0001
title: "lifecycle – Status approved → review bei Hash-Änderung"
level: unit
spec: SPEC-0010
contract: CON-0037
status: draft
framework: pytest
artifact: "tests/unit/test_lifecycle.py"
tags: ["lifecycle", "status-transition", "approved"]
---

# Test: Status-Übergang approved → review

Unit-Tests für `lifecycle.check_transitions()` und `apply_transitions()`.

## Test Cases

| TC    | Beschreibung                                                             | Erwartet                             |
|-------|--------------------------------------------------------------------------|--------------------------------------|
| TC-01 | approved-Spec mit geändertem Body → check_transitions liefert Übergang  | StatusChange mit new_status=review   |
| TC-02 | apply_transitions patcht Frontmatter in Datei                             | Datei enthält `status: review`       |
| TC-03 | apply_transitions aktualisiert content-hashes.json                       | Neuer Hash gespeichert               |
| TC-04 | implemented-Spec mit geändertem Body → Übergang nach review              | old_status=implemented, new_status=review |
