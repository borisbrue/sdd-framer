---
id: TST-0206
project: PRJ-0001
title: "sdd vision stats – Ausgabe und Fehlerverhalten"
level: unit
spec: SPEC-0047
contract: CON-0180
status: draft
framework: pytest
artifact: "tests/unit/test_tst_0206.py"
tags:
  - vision
  - stats
  - cli
---

# Test: sdd vision stats – Ausgabe und Fehlerverhalten

> **Level:** unit · **Spec:** SPEC-0047 · **Contract:** CON-0180

## Was wird geprüft?

Prüft das `sdd vision stats` CLI-Kommando: korrekte Ausgabe aller vier
Statistik-Kategorien, Zahlen aus einer konkreten VisionDocument-Instanz,
Exit-Code 0 bei vorhandener vision.md, Fehlermeldung + Exit-Code ≠ 0 bei
fehlender vision.md.

## Vorbedingungen

- `sdd vision stats` ist als Click-Befehl in `tool.sdd_cli.main` registriert
- `VisionStats.from_document()` und `VisionDocument.from_file()` sind implementiert
- Click CliRunner für isolierte Tests verfügbar

## Ablauf

1. Temporäre vision.md mit bekannten Werten erstellen
2. `sdd vision stats` via CliRunner aufrufen
3. Output-Strings und Exit-Code prüfen
4. Test mit fehlender vision.md: Fehlermeldung + Exit-Code ≠ 0

## Verknüpfung mit Contract (CON-0180)

- [x] INV-01: VisionStats.from_document() — keine Datei-I/O in der Statistik-Berechnung
- [x] INV-02: Ausgabe enthält alle vier Kategorien (Features, Tasks, LLM, Code Challenges)
- [x] INV-03: Fehlermeldung + sdd vision init Hinweis bei fehlender vision.md
- [x] INV-04: VisionStats ist unveränderlich (frozen dataclass)
- [x] Szenario: vollständige Vision → korrekte Zahlen
- [x] Szenario: leeres Skelett → alle Zahlen 0
- [x] Szenario: fehlende Datei → Exit-Code ≠ 0
