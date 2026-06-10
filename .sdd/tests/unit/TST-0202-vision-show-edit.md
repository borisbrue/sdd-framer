---
id: TST-0202
project: PRJ-0001
title: "sdd vision show und sdd vision edit"
level: unit
spec: SPEC-0046
contract: CON-0176
status: draft
framework: pytest
artifact: "tests/unit/test_tst_0202.py"
tags:
  - vision
  - show
  - edit
---

# Test: sdd vision show und sdd vision edit

> **Level:** unit · **Spec:** SPEC-0046 · **Contract:** CON-0176

## Was wird geprüft?

Prüft `VisionReader.show()` und `VisionEditor.open()`: Ausgabe des Dokuments,
$EDITOR-Fallback-Verhalten, Fehlerfall bei fehlender Vision.

## Vorbedingungen

- `tool.sdd_cli.vision.show.VisionReader` existiert
- `tool.sdd_cli.vision.edit.VisionEditor` existiert

## Ablauf

1. tmp-Vision-Datei anlegen
2. show/edit mit verschiedenen ENV-Zuständen aufrufen
3. stdout-Ausgabe und Exit-Code prüfen

## Verknüpfung mit Contract (CON-0176)

- [x] INV-01: Fehler wenn `.sdd/vision.md` fehlt, Exit-Code != 0
- [x] INV-02: show verändert Datei nicht
- [x] INV-03: edit öffnet $EDITOR; ohne $EDITOR → Pfad ausgeben + Exit 0
- [x] INV-04: edit wartet nicht auf Editor-Prozess
