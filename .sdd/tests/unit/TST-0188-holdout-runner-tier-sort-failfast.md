---
id: TST-0188
title: "Holdout-Runner: Tier-Sortierung und Fail-Fast (Unit)"
spec: SPEC-0042
contract: CON-0163
level: unit
artifact: "tests/unit/test_tst_0188.py"
status: draft
---

# Test: Holdout-Runner Tier-Sortierung und Fail-Fast

> **Contract:** CON-0163 · **Spec:** SPEC-0042 · **Level:** unit

## Testfälle

| TC | Beschreibung                                              | Erwartet             |
|----|-----------------------------------------------------------|----------------------|
| 01 | critical fail → normal und edge-case werden übersprungen | normal/edge: skipped |
| 02 | normal fail → edge-case wird übersprungen                 | edge-case: skipped   |
| 03 | alle bestehen → alle ausgeführt                           | 3× passed            |
| 04 | Sortierung: edge-case zuerst input → critical zuerst output | PRIORITY_ORDER       |
| 05 | priority-Feld fehlt im Frontmatter → Fallback "normal"   | kein Fehler          |
