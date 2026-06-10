---
id: TST-0205
project: PRJ-0001
title: ".sdd/vision.md Dokumentstruktur und Schema"
level: unit
spec: SPEC-0046
contract: CON-0179
status: draft
framework: pytest
artifact: "tests/unit/test_tst_0205.py"
tags:
  - vision
  - schema
  - document
---

# Test: .sdd/vision.md Dokumentstruktur und Schema

> **Level:** unit · **Spec:** SPEC-0046 · **Contract:** CON-0179

## Was wird geprüft?

Prüft `VisionDocument` Parser und Validator: alle Pflicht-Überschriften vorhanden,
Feature-Format (nummeriert, Blockquote-Ergebnisse), Task-Format (Checkbox),
kein YAML-Frontmatter, genau eine Vision-Datei pro Projekt.

## Vorbedingungen

- `tool.sdd_cli.vision.document.VisionDocument` existiert
- `VisionDocument.from_file(path)` parst `.sdd/vision.md`
- `VisionDocument.validate()` prüft Schema-Konformität

## Ablauf

1. Verschiedene Markdown-Strings parsen
2. Schema-Konformität prüfen
3. Fehlerfälle (fehlende Überschriften, falsches Format) testen

## Verknüpfung mit Contract (CON-0179)

- [x] INV-01: Pro Projekt genau eine Vision-Datei (Singleton-Guard in VisionDocument)
- [x] INV-02: Alle 7 Pflicht-Überschriften vorhanden (auch wenn leer)
- [x] INV-03: Freitext-Abschnitte akzeptieren beliebigen Markdown-Inhalt
- [x] INV-04: Features als nummerierte Liste + optionale Blockquote-Zeilen
- [x] INV-05: Tasks als Checkbox-Liste `- [ ] / - [x]`
- [x] INV-06: Kein YAML-Frontmatter-Block erlaubt
