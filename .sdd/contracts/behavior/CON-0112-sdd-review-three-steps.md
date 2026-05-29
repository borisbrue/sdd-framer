---
id: CON-0112
title: "/sdd-review – Dreistufiger Review (SOLID + Pattern + Regression)"
type: behavior
format: gherkin
spec: SPEC-0029
version: 0.1.0
status: approved
artifact: "contracts/behavior/sdd-review-three-steps.feature"
tests:
- TST-0131
---

# Contract: /sdd-review – Dreistufiger Review (SOLID + Pattern + Regression)

> **Spec:** SPEC-0029 · **Typ:** Verhalten (Gherkin) · **Status:** draft

## Zweck

Stellt sicher, dass `/sdd-review SPEC-XXXX` drei dokumentierte Unterschritte
durchläuft: SOLID-Check (`sdd solid-check`), Pattern-Check (`sdd pattern-suggest`)
und Regression-Check (`sdd regression-check`). Der Regression-Check ist neu und
prüft Konflikte mit Contracts bereits implementierter Specs.

**Precondition:** `sdd regression-check` muss als CLI-Befehl verfügbar sein (implementiert in SPEC-0029). Solange der Befehl nicht existiert, wird Schritt 3 übersprungen und der Nutzer mit `[WARN] sdd regression-check nicht verfügbar` informiert.

## Garantien

- `sdd solid-check SPEC-XXXX` wird ausgeführt und das Ergebnis angezeigt
- `sdd pattern-suggest SPEC-XXXX` wird ausgeführt; jeder Vorschlag wird interaktiv bestätigt oder abgelehnt
- `sdd regression-check SPEC-XXXX` wird ausgeführt und das Ergebnis angezeigt
- Die Reihenfolge ist immer: SOLID → Pattern → Regression (Chain of Responsibility)
- Bei `error`-Severity im Regression-Check wird der Nutzer explizit gewarnt bevor fortgefahren wird

## Invarianten

- **INV-01:** Alle drei Schritte werden ausgeführt — keiner darf übersprungen werden.
- **INV-02:** Pattern-Vorschläge werden nicht automatisch angenommen; jeder erfordert explizite Nutzerbestätigung.
- **INV-03:** Bei Regression-`error` erscheint eine Warnung; der Nutzer entscheidet ob weiter oder abbrechen.

## Szenarien (Gherkin)

```gherkin
Feature: /sdd-review – Dreistufiger Review-Flow

  Scenario: Happy Path – alle drei Schritte laufen durch
    Given SPEC-XXXX existiert mit status: draft
    When /sdd-review SPEC-XXXX aufgerufen wird
    Then wird sdd solid-check SPEC-XXXX ausgeführt und das Ergebnis angezeigt
    And wird sdd pattern-suggest SPEC-XXXX ausgeführt
    And wird sdd regression-check SPEC-XXXX ausgeführt und das Ergebnis angezeigt
    And die Reihenfolge ist SOLID → Pattern → Regression (INV-01)

  Scenario: Pattern-Vorschlag erfordert Bestätigung
    Given sdd pattern-suggest liefert einen Vorschlag "Strategy"
    When /sdd-review SPEC-XXXX den Pattern-Schritt ausführt
    Then fragt der Skill "Annehmen? (ja/nein/überspringen)"
    And wartet auf explizite Nutzerantwort (INV-02)

  Scenario: Regression-Check meldet error-Severity
    Given sdd regression-check findet einen Endpoint-Konflikt mit CON-0001
    When /sdd-review SPEC-XXXX den Regression-Schritt ausführt
    Then erscheint eine Warnung: "⚠ Regression-Konflikt gefunden: CON-XXXX vs. CON-0001"
    And der Nutzer entscheidet ob weiter oder abbrechen (INV-03)

  Scenario: Regression-Check meldet warning-Severity
    Given sdd regression-check findet eine Schema-Überschneidung mit CON-0002
    And das LLM bewertet den Fall als "warning"
    When /sdd-review SPEC-XXXX den Regression-Schritt ausführt
    Then erscheint "⚠ Möglicher Konflikt (warning): CON-XXXX vs. CON-0002 – bitte prüfen"
    And der Review-Flow fährt automatisch fort ohne Nutzerunterbrechung

  Scenario: Regression-Check findet keine Konflikte
    Given keine implementierten Specs haben überlappende Contracts
    When sdd regression-check SPEC-XXXX ausgeführt wird
    Then erscheint "✓ Kein Regressionsrisiko gefunden"
    And der Review-Flow fährt normal fort
```

## Begriffe

| Begriff | Definition |
|---|---|
| Chain of Responsibility | Jeder Review-Handler (SOLID/Pattern/Regression) läuft sequenziell und ist unabhängig erweiterbar |
| error-Severity | Konfliktstufe die explizite Nutzerentscheidung erfordert (im Gegensatz zu `warning`) |
| Regression-Check | Prüfung ob neue Contracts mit Contracts bereits implementierter Specs kollidieren |
