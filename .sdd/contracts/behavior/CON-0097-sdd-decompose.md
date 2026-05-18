---
id: CON-0097
title: "sdd decompose – Task-Ableitung und Klassifizierung aus Spec"
type: behavior
format: gherkin
spec: SPEC-0026
version: 0.1.0
status: draft
artifact: "contracts/behavior/sdd-decompose.feature"
tests:
- TST-0116
---

# Contract: sdd decompose – Task-Ableitung und Klassifizierung aus Spec

> **Spec:** SPEC-0026 · **Typ:** Verhalten (Gherkin) · **Status:** draft

## Zweck

Legt fest, wie `sdd decompose SPEC-XXXX` ein Spec in atomare, klassifizierte
Tasks zerlegt und dem Entwickler zur interaktiven Bestätigung vorlegt (FR-01–03).

## Garantien

- Jede FR des Specs wird in mindestens einem Task abgebildet.
- Kein Task adressiert mehr als eine funktionale Verantwortlichkeit.
- Jeder Task erhält Komplexität (low/medium/high), Kontextgröße (S/M/L) und Typ.
- Der Entwickler kann Tasks vor der Ausführung bearbeiten, entfernen oder hinzufügen.
- Erst nach expliziter Bestätigung werden Tasks persistiert und verteilt.

## Invarianten

- **INV-01:** Leere Task-Liste (0 Tasks) ist ein Fehler – Abbruch mit Meldung.
- **INV-02:** Zwei Tasks mit identischem Titel im selben Spec sind unzulässig.
- **INV-03:** `estimated_tokens` > 0 für jeden Task.

## Szenarien (Gherkin)

```gherkin
Feature: sdd decompose

  Scenario: Erfolgreiche Dekomposition mit Bestätigung
    Given ein valides Spec "SPEC-0026" mit 16 FRs
    When ich "sdd decompose SPEC-0026" ausführe
    Then erhalte ich eine Task-Liste mit mindestens 5 Tasks
    And jeder Task hat complexity, context_size und type gesetzt
    When ich die Liste mit "ja" bestätige
    Then werden die Tasks als JSON in ".sdd/tasks/SPEC-0026.json" gespeichert

  Scenario: Entwickler bearbeitet Task vor Bestätigung
    Given eine generierte Task-Liste für SPEC-0026
    When ich Task 3 mit neuem Titel editiere
    Then spiegelt die gespeicherte Liste den aktualisierten Titel wider

  Scenario: Leere Spec liefert Fehler
    Given ein Spec ohne Funktionale Anforderungen
    When ich "sdd decompose SPEC-XXXX" ausführe
    Then erhalte ich Exit-Code 1 und Meldung "Keine Tasks ableitbar"
```

## Begriffe

| Begriff | Definition |
|---|---|
| Atomar | Ein Task adressiert genau eine funktionale Verantwortlichkeit |
| Klassifizierung | Kombination aus Komplexität, Kontextgröße und Typ |
