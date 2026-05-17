---
id: TST-0026
project: PRJ-0001
title: "patch_status – Unit Test"
level: unit
spec: SPEC-0007
contract: CON-0020
status: implemented
framework: pytest
artifact: "tests/unit/test_execute_flow.py"
tags: ["frontmatter", "patch-status", "execute-flow"]
---

# Test: patch_status – Unit Test

Unit-Tests für `frontmatter.patch_status(path, new_status)`.

## Test Cases

| TC    | Beschreibung                                          | Erwartet                    |
|-------|-------------------------------------------------------|-----------------------------|
| TC-01 | Ändert status-Feld auf neuen Wert                     | Datei enthält neuen Status  |
| TC-02 | Behält restliches Frontmatter unverändert             | Alle anderen Felder gleich  |
| TC-03 | Behält Body unverändert                               | Body identisch              |
| TC-04 | Überschreibt vorhandenen Status korrekt               | Kein doppeltes status-Feld  |
