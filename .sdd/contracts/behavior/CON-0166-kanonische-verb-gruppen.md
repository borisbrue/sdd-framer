---
id: CON-0166
project: PRJ-0001
title: "Kanonische Verb-Gruppen `sdd new` und `sdd review`"
type: behavior
format: markdown
spec: SPEC-0044
version: 0.1.0
status: approved
artifact: "contracts/behavior/kanonische-verb-gruppen.md"
tests:
  - TST-0194
---

# Contract: Kanonische Verb-Gruppen `sdd new` und `sdd review`

> **Spec:** SPEC-0044 · **Typ:** Verhalten · **Status:** draft

## Zweck

Garantiert, dass `sdd new` der einzige Einstiegspunkt für Erstellung und
`sdd review` der einzige Einstiegspunkt für Reviews ist. Alle umbenannten
Befehle sind unter den neuen Namen erreichbar; alte Namen liefern einen
Fehler mit Migrationshinweis.

## Garantien

### `sdd new` (Erstellung)
- `sdd new spec|contract|test|holdout|hotfix` sind alle aufrufbar
- Kein `sdd spec new` oder `sdd contract new` existiert mehr als öffentlicher Befehl

### `sdd review` (Review)
- `sdd review spec SPEC-ID` führt SOLID-Analyse + Pattern-Vorschläge durch
- `sdd review contract CON-ID` führt LLM-Review des Contract-Inhalts durch
- `sdd review contract --spec SPEC-ID` iteriert über alle Contracts des Specs sequenziell
- `sdd review pending [--auto]` listet Contracts im Status `review` auf

### Namenskollision aufgelöst
- `sdd contract analyze SPEC-ID CON-ID…` ersetzt `sdd contract review` für die
  Konfliktanalyse zwischen Contracts
- `sdd contract review` existiert nicht mehr (gibt `unknown command` + Hinweis auf
  `sdd contract analyze` bzw. `sdd review contract`)

### Weitere Umbenennungen
- `sdd holdout generate SPEC-ID` ersetzt `sdd generate-holdouts SPEC-ID`
- `sdd holdout run` ersetzt `sdd evaluate`
- `sdd test run SPEC-ID` ersetzt `sdd test-run SPEC-ID`
- `sdd test results SPEC-ID` ersetzt `sdd test-results SPEC-ID`

## Invarianten

- Jede alte Befehlsform mit Exit ≠ 0 und Text "umbenannt zu" oder "unbekannter Befehl"
- Alle neuen Befehlsformen mit Exit 0 und korrekter Ausgabe
- `sdd --help` zeigt `new` und `review` als eigenständige Gruppen

## Gherkin

```gherkin
Feature: Kanonische Verb-Gruppen nach Cleanup

  Scenario: sdd new hotfix ist neu verfügbar
    When ich `sdd new hotfix --help` aufrufe
    Then endet der Prozess mit Exit-Code 0

  Scenario: sdd review spec funktioniert
    When ich `sdd review spec SPEC-0044` aufrufe
    Then führt der Befehl SOLID-Analyse und Pattern-Prüfung durch
    And endet mit Exit-Code 0

  Scenario: sdd review contract --spec iteriert über alle Contracts
    Given SPEC-0044 hat mehrere Contracts im Status draft
    When ich `sdd review contract --spec SPEC-0044` aufrufe
    Then wird jeder draft-Contract sequenziell reviewed

  Scenario: sdd contract analyze löst alte review-Namenskollision auf
    When ich `sdd contract analyze SPEC-0044` aufrufe
    Then führt der Befehl die Konfliktanalyse durch (nicht das LLM-Review)

  Scenario: alter Befehl gibt Hinweis
    When ich `sdd generate-holdouts SPEC-0044` aufrufe
    Then endet der Prozess mit Exit-Code ungleich 0
    And die Ausgabe enthält "sdd holdout generate"
```
