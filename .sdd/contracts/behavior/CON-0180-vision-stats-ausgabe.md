---
id: CON-0180
project: PRJ-0001
title: "sdd vision stats – Ausgabe und Fehlerverhalten"
type: behavior
format: gherkin
spec: SPEC-0047
version: 0.1.0
status: approved
artifact: ""
tests:
- TST-0206
---

# Contract: sdd vision stats – Ausgabe und Fehlerverhalten

> **Spec:** SPEC-0047 · **Typ:** Verhalten (Gherkin) · **Status:** draft

## Zweck

Definiert das beobachtbare Verhalten von `sdd vision stats`: die Berechnung
und formatierte Ausgabe von Vision-Statistiken sowie das Verhalten wenn
`.sdd/vision.md` nicht existiert.

## Invarianten

- **INV-01:** `VisionStats.from_document(doc)` liest ausschließlich aus dem
  übergebenen `VisionDocument` — keine Datei-I/O, keine Seiteneffekte.
- **INV-02:** Die Ausgabe enthält immer alle vier Kategorien:
  Features, Tasks (gesamt / done / offen), LLM Challenges, Code Challenges.
- **INV-03:** Fehlt `.sdd/vision.md`, gibt der Befehl eine Fehlermeldung
  mit Hinweis auf `sdd vision init` aus — Exit-Code ≠ 0.
- **INV-04:** `VisionStats` ist ein unveränderliches Value Object
  (keine Setter, keine Mutation nach Erstellung).

## Gherkin-Szenarien

```gherkin
Feature: sdd vision stats – Ausgabe und Fehlerverhalten

  Scenario: Statistiken einer vollständigen Vision ausgeben
    Given `.sdd/vision.md` existiert mit 3 Features und 5 Tasks (2 done)
    And Feature 1 hat LLM-Challenge und Code-Challenge
    And Feature 2 hat nur LLM-Challenge
    When der Nutzer `sdd vision stats` ausführt
    Then enthält die Ausgabe "Features:        3"
    And enthält "Tasks:           5  (done: 2 / offen: 3)"
    And enthält "LLM Challenges:  2"
    And enthält "Code Challenges: 1"
    And der Exit-Code ist 0

  Scenario: Leere Vision (nur Skelett-Dokument)
    Given `.sdd/vision.md` existiert als Skelett-Dokument ohne Features und Tasks
    When der Nutzer `sdd vision stats` ausführt
    Then enthält die Ausgabe "Features:        0"
    And enthält "Tasks:           0  (done: 0 / offen: 0)"
    And enthält "LLM Challenges:  0"
    And enthält "Code Challenges: 0"
    And der Exit-Code ist 0

  Scenario: vision.md fehlt
    Given kein `.sdd/vision.md` existiert
    When der Nutzer `sdd vision stats` ausführt
    Then enthält die Ausgabe eine Fehlermeldung mit Hinweis auf "sdd vision init"
    And der Exit-Code ist nicht 0
```
