---
id: TST-0203
project: PRJ-0001
title: "sdd vision add-feature und sdd vision add-task"
level: unit
spec: SPEC-0046
contract: CON-0177
status: draft
framework: pytest
artifact: "tests/unit/test_tst_0203.py"
tags:
  - vision
  - add-feature
  - add-task
---

# Test: sdd vision add-feature und sdd vision add-task

> **Level:** unit · **Spec:** SPEC-0046 · **Contract:** CON-0177

## Was wird geprüft?

Prüft `VisionDocument.add_feature()` und `VisionDocument.add_task()`:
Index-Fortlauf, Pflichtfeld-Validierung, Unveränderlichkeit bestehender Einträge.

## Vorbedingungen

- `tool.sdd_cli.vision.document.VisionDocument` existiert
- `add_feature(title, description)` und `add_task(title)` sind Methoden

## Ablauf

1. `VisionDocument` aus tmp-Datei laden
2. Features und Tasks hinzufügen
3. Datei-Inhalt gegen erw. Markdown-Struktur prüfen

## Verknüpfung mit Contract (CON-0177)

- [x] INV-01: nummerierte Liste, 1-basierter fortlaufender Index
- [x] INV-02: Tasks als Checkbox-Liste `- [ ] Titel`
- [x] INV-03: Fehler wenn `.sdd/vision.md` fehlt
- [x] INV-04: Leerer Titel → ValueError
- [x] INV-05: Kein Lifecycle, keine Contract-Bindung (Felder nicht vorhanden)
- [x] INV-06: Bestehende Einträge incl. Challenge-Ergebnisse unverändert
