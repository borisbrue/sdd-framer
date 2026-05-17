---
id: TST-0051
project: PRJ-0001
title: "new_contract – initiales Status ist review, nicht draft"
level: unit
spec: SPEC-0010
contract: CON-0037
status: draft
framework: pytest
artifact: "tests/unit/test_lifecycle.py"
tags: ["lifecycle", "new-contract", "initial-status"]
---

# Test: sdd new contract → Status review

Unit-Test für FR-03: `sdd new contract` setzt Status auf `review`.

## Test Cases

| TC    | Beschreibung                                                        | Erwartet                         |
|-------|---------------------------------------------------------------------|----------------------------------|
| TC-01 | Erstellter Contract hat `status: review` im Frontmatter            | `doc.frontmatter["status"] == "review"` |
| TC-02 | Der automatisch mitgenerierte Test-Stub hat `status: draft`        | TST-Status unverändert `draft`   |
