---
id: CON-0111
title: "/sdd-new spec – Kein validate-Aufruf nach dem Speichern"
type: behavior
format: gherkin
spec: SPEC-0029
version: 0.1.0
status: approved
artifact: "contracts/behavior/sdd-new-spec-no-validate.feature"
tests:
- TST-0130
---

# Contract: /sdd-new spec – Kein validate-Aufruf nach dem Speichern

> **Spec:** SPEC-0029 · **Typ:** Verhalten (Gherkin) · **Status:** draft

## Zweck

Stellt sicher, dass der `/sdd-new spec`-Skill nach dem Speichern einer neuen Spec
keinen `sdd validate`-Aufruf ausführt. Eine frisch angelegte Spec hat noch keine
Contracts und Tests — eine Validierung würde zwingend fehlschlagen und den Nutzer
mit irreführenden Fehlermeldungen konfrontieren.

## Garantien

- Nach dem Speichern der Spec-Datei wird `sdd validate` weder direkt noch indirekt aufgerufen
- Der Skill gibt stattdessen einen Hinweis auf den nächsten Schritt aus: `/sdd-review SPEC-XXXX`
- Der Skill bricht bei Bestätigungsverweigerung ab ohne die Datei zu schreiben

## Invarianten

- **INV-01:** `sdd validate` darf im `/sdd-new spec`-Flow an keiner Stelle aufgerufen werden.
- **INV-02:** Der Hinweis auf `/sdd-review SPEC-XXXX` muss die konkrete ID der soeben erstellten Spec enthalten. Kann die ID nicht ermittelt werden, bricht der Skill mit einer klaren Fehlermeldung ab statt eine falsche ID auszugeben.

## Szenarien (Gherkin)

```gherkin
Feature: /sdd-new spec – kein vorzeitiger validate-Aufruf

  Scenario: Neue Spec wird gespeichert – kein validate
    Given kein Contract und kein Test für SPEC-XXXX existieren
    When der Nutzer /sdd-new spec durchführt und bestätigt
    Then wird die Spec-Datei unter ".sdd/specs/SPEC-XXXX-<slug>.md" gespeichert
    And sdd validate wird NICHT aufgerufen (INV-01)
    And der Skill gibt aus: "Nächster Schritt: /sdd-review SPEC-XXXX" (INV-02)

  Scenario: Nutzer verweigert Bestätigung
    Given der Skill hat die Spec zur Vorschau angezeigt
    When der Nutzer mit "nein" antwortet
    Then wird keine Datei geschrieben
    And sdd validate wird nicht aufgerufen (INV-01)

  Scenario: Spec mit abhängiger SPEC-ID
    Given der Nutzer gibt "depends_on: SPEC-0001" an
    When der Nutzer /sdd-new spec durchführt und bestätigt
    Then enthält das Frontmatter "depends_on: [\"SPEC-0001\"]"
    And sdd validate wird NICHT aufgerufen (INV-01)
```

## Begriffe

| Begriff | Definition |
|---|---|
| Slug | Kleinbuchstaben-Kebab-Case-Version des Spec-Titels (z.B. "refactoring-of-sdd-implement") |
| Nächster-Schritt-Hinweis | Ausgabe am Ende des Flows mit konkreter SPEC-ID und Skill-Name |
