---
id: TST-0207
project: PRJ-0001
title: "VisionStats – Value Object Schema"
level: unit
spec: SPEC-0047
contract: CON-0181
status: draft
framework: pytest
artifact: "tests/unit/test_tst_0207.py"
tags:
  - vision
  - stats
  - value-object
---

# Test: VisionStats – Value Object Schema

> **Level:** unit · **Spec:** SPEC-0047 · **Contract:** CON-0181

## Was wird geprüft?

Prüft `VisionStats` als frozen Dataclass: alle Felder vorhanden, Typen korrekt,
Invarianten (task_done + task_open == task_total, keine Negativwerte,
challenge_count <= feature_count), `from_document()` als einzige Factory,
`ValueError` bei INV-Verletzungen.

## Vorbedingungen

- `tool.sdd_cli.vision.stats.VisionStats` existiert
- `VisionStats.from_document(doc: VisionDocument) -> VisionStats` implementiert
- `VisionDocument` aus SPEC-0046 verwendbar (echte Klasse, kein Mock)

## Ablauf

1. `from_document()` mit verschiedenen Dokumenten aufrufen
2. Felder und Invarianten prüfen
3. Frozen-Test: Setzen eines Feldes → AttributeError/FrozenInstanceError
4. Invariant-Verletzung: `from_document()` aus einem konsistenten Dokument
   → alle INVs automatisch erfüllt

## Verknüpfung mit Contract (CON-0181)

- [x] INV-01: task_done + task_open == task_total
- [x] INV-02: alle Felder >= 0
- [x] INV-03: challenge_count <= feature_count
- [x] INV-04: frozen (keine Mutation nach Erstellung)
- [x] INV-05: from_document() als einzige Factory
- [x] Schema: alle 6 Felder vorhanden und korrekt berechnet
