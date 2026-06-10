---
id: CON-0170
project: PRJ-0001
title: "Verantwortlichkeitstrennung: `sdd review contract` vs. `sdd test generate`"
type: behavior
format: markdown
spec: SPEC-0044
version: 0.1.0
status: approved
artifact: "contracts/behavior/review-contract-verantwortlichkeit.md"
tests:
  - TST-0198
---

# Contract: Verantwortlichkeitstrennung `sdd review contract` vs. `sdd test generate`

> **Spec:** SPEC-0044 · **Typ:** Verhalten · **Status:** draft

## Zweck

Garantiert, dass `sdd review contract` ausschließlich den Contract-Inhalt reviewt
und den Status auf `approved` setzt — ohne Nebenwirkung auf Test-Dateien.
Test-Stubs werden ausschließlich über `sdd test generate SPEC-ID [CON-ID…]` erstellt.

## Garantien

### `sdd review contract CON-ID`
- Prüft Vollständigkeit, SOLID-Konformität und Klarheit des Contract-Inhalts
- Setzt `status: approved` im Contract-Frontmatter
- Legt **keine** TST-Datei an (weder Stub noch Volltest)
- Ändert **keine** anderen Dateien außer dem Contract selbst

### `sdd test generate SPEC-ID [CON-ID…]`
- Ist der einzige Befehl, der TST-Dateien anlegt
- Lädt den Spec-Kontext via SPEC-ID (vollständige Abhängigkeits-Informationen)
- Ohne `CON-ID…`-Filter: generiert Tests für alle approved Contracts des Specs
- Mit `CON-ID…`-Filter: generiert Tests nur für die genannten Contracts
- Doppelte Stubs sind unmöglich (idempotent: vorhandene TST-Datei wird aktualisiert,
  nicht neu angelegt)

## Invarianten

- Nach `sdd review contract CON-ID`: Anzahl TST-Dateien im Projekt unverändert
- Nach `sdd test generate SPEC-ID`: mindestens eine TST-Datei neu oder aktualisiert
- Kein Befehl außer `sdd test generate` schreibt in `.sdd/tests/`

## Gherkin

```gherkin
Feature: Trennung Review und Test-Generierung

  Scenario: sdd review contract legt keine TST-Datei an
    Given CON-0165 ist im Status draft
    And es existiert noch keine TST-Datei für CON-0165
    When ich `sdd review contract CON-0165` aufrufe
    Then wird CON-0165.status auf "approved" gesetzt
    And keine neue Datei in .sdd/tests/ wurde angelegt

  Scenario: sdd test generate erstellt TST-Dateien
    Given alle Contracts von SPEC-0044 sind approved
    When ich `sdd test generate SPEC-0044` aufrufe
    Then werden TST-Dateien für alle approved Contracts angelegt
    And jede TST-Datei enthält den Spec-Kontext aus SPEC-0044

  Scenario: sdd test generate ist idempotent
    Given TST-0200 existiert bereits für CON-0165
    When ich `sdd test generate SPEC-0044 CON-0165` erneut aufrufe
    Then wird TST-0200 aktualisiert (nicht dupliziert)
    And es existiert weiterhin genau eine TST-Datei für CON-0165

  Scenario: sdd review contract --spec iteriert korrekt
    Given SPEC-0044 hat Contracts CON-0165 bis CON-0170 im Status draft
    When ich `sdd review contract --spec SPEC-0044` aufrufe
    Then wird für jeden Contract sequenziell sdd review contract CON-XXXX aufgerufen
    And keine TST-Dateien werden angelegt
```
