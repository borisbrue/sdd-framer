---
id: TST-0201
project: PRJ-0001
title: "sdd vision init – Wizard und Idempotenz-Guard"
level: unit
spec: SPEC-0046
contract: CON-0175
status: draft
framework: pytest
artifact: "tests/unit/test_tst_0201.py"
tags:
  - vision
  - init
  - wizard
  - idempotenz
---

# Test: sdd vision init – Wizard und Idempotenz-Guard

> **Level:** unit · **Spec:** SPEC-0046 · **Contract:** CON-0175

## Was wird geprüft?

Prüft `VisionInitWizard.run()`: Erstellung von `.sdd/vision.md` mit Wizard-Eingaben,
Skelett-Dokument bei leeren Feldern, Idempotenz-Guard bei bestehender Datei,
und optionaler Vision-Schritt in `sdd init`.

## Vorbedingungen

- `tool.sdd_cli.vision.init.VisionInitWizard` existiert
- `VisionInitWizard.run(sdd_dir, answers)` erzeugt `.sdd/vision.md`
- `VisionDocument` aus `tool.sdd_cli.vision.document` ist importierbar

## Ablauf

1. `VisionInitWizard` mit tmp-Verzeichnis instanziieren
2. Verschiedene Antwort-Kombinationen (voll/leer/fehlend) testen
3. Datei-Inhalt und Exit-Verhalten prüfen

## Verknüpfung mit Contract (CON-0175)

- [x] INV-01: genau `.sdd/vision.md`, keine weiteren Dateien
- [x] INV-02: Idempotenz-Guard — Abbruch wenn Datei bereits existiert
- [x] INV-03: Leere Felder → gültiges Skelett-Dokument
- [x] INV-04: sdd init — Vision-Schritt optional überspringbar
- [x] INV-05: Erzeugtes Dokument entspricht CON-0179-Schema (Pflicht-Überschriften)
