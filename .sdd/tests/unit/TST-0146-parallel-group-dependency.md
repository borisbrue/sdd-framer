---
id: TST-0146
project: ""
title: "Tests: parallel_group Dependency-Auflösung + Zirkel-Erkennung (SPEC-0034)"
contract: CON-0124
contracts: ["CON-0124"]
spec: SPEC-0034
level: unit
status: draft
artifact: "tests/unit/test_tst_0146.py"
---

# Test: parallel_group und Circular Dependency Detection (SPEC-0034)

> **Contract:** CON-0124 · **Typ:** Unit-Test · **Status:** draft

## Abgedeckte Garantien

- SPEC-0034 FR-04: parallel_group-Annotation auf Task-Modell-Ebene
- detect_circular_dependencies(): Erkennt direkte, indirekte und Selbst-Zyklen
- CON-0124 INV-04 (zirkuläre Deps): Tasks mit Zirkeln werden geblockt
- Task.to_dict() / Task.from_dict() Roundtrip für alle neuen SPEC-0034-Felder
