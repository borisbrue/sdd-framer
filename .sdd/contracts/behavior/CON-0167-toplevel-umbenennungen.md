---
id: CON-0167
project: PRJ-0001
title: "Top-Level-Befehle in Gruppen `sdd spec` und `sdd autonomy` eingeordnet"
type: behavior
format: markdown
spec: SPEC-0044
version: 0.1.0
status: approved
artifact: "contracts/behavior/toplevel-umbenennungen.md"
tests:
  - TST-0195
---

# Contract: Top-Level-Befehle in Gruppen eingeordnet

> **Spec:** SPEC-0044 · **Typ:** Verhalten · **Status:** draft

## Zweck

Garantiert, dass lose Top-Level-Befehle in die Gruppen `sdd spec` und
`sdd autonomy` überführt werden und `sdd status-check` nicht mehr als
öffentlicher Befehl exponiert ist.

## Garantien

### `sdd spec`-Gruppe (erweitert)
- `sdd spec solid ARTIFACT-ID` führt SOLID-Analyse durch (war: `sdd solid-check`)
- `sdd spec regression SPEC-ID` führt Regression-Check durch (war: `sdd regression-check`)

### `sdd autonomy`-Gruppe (neu)
- `sdd autonomy false-positive PR-NR` markiert einen False-Positive (war: `sdd mark-false-positive`)
- `sdd autonomy level PROJECT-ID` zeigt Autonomie-Level (war: `sdd level`)
- `sdd autonomy set-level PROJECT-ID LEVEL` setzt Autonomie-Level (war: `sdd set-level`)

### `sdd status-check` — intern
- `sdd status-check` ist nicht mehr als öffentlicher CLI-Befehl verfügbar
- Der Befehl wird intern von pre-commit-Hook und `sdd spec start` aufgerufen
- Ein direkter Aufruf per User/LLM endet mit Exit ≠ 0 und Hinweis auf internen Status

## Invarianten

- Alle alten Top-Level-Formen liefern Exit ≠ 0 + Migrationshinweis auf neuen Namen
- `sdd --help` zeigt `solid-check`, `regression-check`, `mark-false-positive`,
  `level`, `set-level` nicht mehr auf der obersten Ebene
- pre-commit-Hook-Funktionalität bleibt erhalten (status-check intern lauffähig)

## Gherkin

```gherkin
Feature: Top-Level-Umbenennungen nach Cleanup

  Scenario: sdd spec solid ersetzt solid-check
    When ich `sdd spec solid SPEC-0044` aufrufe
    Then führt der Befehl die SOLID-Analyse durch
    And endet mit Exit-Code 0

  Scenario: sdd spec regression ersetzt regression-check
    When ich `sdd spec regression SPEC-0044` aufrufe
    Then führt der Befehl den Regression-Check durch
    And endet mit Exit-Code 0

  Scenario: sdd autonomy level funktioniert
    When ich `sdd autonomy level PRJ-0001` aufrufe
    Then gibt der Befehl das aktuelle Autonomie-Level aus
    And endet mit Exit-Code 0

  Scenario: sdd status-check ist nicht mehr öffentlich
    When ich `sdd status-check` aufrufe
    Then endet der Prozess mit Exit-Code ungleich 0
    And die Ausgabe enthält "intern"

  Scenario: pre-commit-Hook nutzt status-check intern
    Given ein Git-Commit-Versuch mit unvollständigen Spec-Artefakten
    When der pre-commit-Hook läuft
    Then läuft die status-check-Logik intern durch
    And der Commit wird geblockt bei Gate-Verletzung
```
