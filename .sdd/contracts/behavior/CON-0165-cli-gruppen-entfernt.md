---
id: CON-0165
project: PRJ-0001
title: "CLI-Gruppen `pattern` und `dev` entfernt"
type: behavior
format: markdown
spec: SPEC-0044
version: 0.1.0
status: approved
artifact: "contracts/behavior/cli-gruppen-entfernt.md"
tests:
  - TST-0193
---

# Contract: CLI-Gruppen `pattern` und `dev` entfernt

> **Spec:** SPEC-0044 · **Typ:** Verhalten · **Status:** draft

## Zweck

Garantiert, dass die CLI-Gruppen `sdd pattern` und `sdd dev` vollständig entfernt
werden, die Gruppen `sdd obsidian` und `sdd pwa` erhalten bleiben, und `CHANGELOG.md`
eine Migrationsnotiz enthält.

## Garantien

- `sdd pattern` und alle Unterkommandos (`pattern-suggest`, `pattern accept`,
  `pattern reject`, `pattern list`) sind nach dem Cleanup nicht mehr aufrufbar
- `sdd dev` und alle Unterkommandos (`start`, `exec`, `close`, `pr`, `build`,
  `push`, `up`, `down`) sind nach dem Cleanup nicht mehr aufrufbar
- `sdd obsidian` bleibt vollständig funktionsfähig
- `sdd pwa` bleibt vollständig funktionsfähig
- `DevContainerManager`-Modul bleibt als interne Dependency erhalten
- `CHANGELOG.md` enthält für jede entfernte Gruppe einen Migrationshinweis

## Invarianten

- Kein Aufruf von `sdd pattern *` oder `sdd dev *` darf mit Exit 0 enden
- `sdd --help` listet weder `pattern` noch `dev` als Gruppe auf
- Obsidian- und PWA-Tests bleiben grün

## Gherkin

```gherkin
Feature: CLI-Cleanup — pattern und dev Gruppen entfernt

  Scenario: sdd pattern liefert Fehler
    When ich `sdd pattern list` aufrufe
    Then endet der Prozess mit Exit-Code ungleich 0
    And die Fehlermeldung enthält "unbekannter Befehl"

  Scenario: sdd dev liefert Fehler
    When ich `sdd dev start` aufrufe
    Then endet der Prozess mit Exit-Code ungleich 0

  Scenario: sdd obsidian funktioniert noch
    When ich `sdd obsidian --help` aufrufe
    Then endet der Prozess mit Exit-Code 0

  Scenario: CHANGELOG enthält Migrationshinweis
    Given die Datei CHANGELOG.md existiert
    Then enthält sie den Text "pattern" im Kontext einer Entfernung
    And enthält sie den Text "dev" im Kontext einer Entfernung
```
