---
id: CON-0048
project: PRJ-0001
title: "SOLID CLI Commands Behavior"
type: behavior
format: gherkin
spec: SPEC-0015
version: 0.1.0
status: review
artifact: ".sdd/contracts/behavior/solid-cli-commands-behavior.feature"
tests: ["TST-0004"]
---

# Contract: SOLID CLI Commands Behavior

> **Spec:** SPEC-0015 · **Typ:** Verhalten (Gherkin) · **Status:** review

## Zweck

Definiert das beobachtbare CLI-Verhalten der neuen Befehle aus SPEC-0015:
`sdd solid-check`, `sdd pattern-suggest`, `sdd pattern-accept`, `sdd pattern-reject`,
`sdd pattern-list`. Jeder Befehl hat definierte Exit-Codes, Ausgabeformate und
Seiteneffekte (Datei-Persistenz).

## Garantien

Die Szenarien sind ausführbare Spezifikation. Jedes MUSS durch einen automatisierten
CLI-Integrationstest (subprocess + assertions) abgedeckt sein.

## Invarianten

- **INV-01:** `sdd solid-check <ID>` gibt Exit-Code 0 wenn `overall_solid_score` ∈ {compliant, warn}; Exit-Code 1 wenn `solid_gate.mode: block` und mindestens eine violation; Exit-Code 0 bei `mode: warn` unabhängig von Violations.
- **INV-02:** `sdd pattern-accept` und `sdd pattern-reject` schreiben immer in `.sdd/patterns/<SPEC-ID>-patterns.json` (Datei wird erstellt wenn nicht vorhanden).
- **INV-03:** `sdd pattern-list` gibt 0 aus wenn keine Patterns registriert sind (kein Fehler).
- **INV-04:** Alle Befehle geben Exit-Code 2 zurück wenn die angegebene ID nicht gefunden wird.
- **INV-05:** `sdd solid-check <ID> --json` gibt valides JSON gemäß CON-0046 aus (nur SOLID-Report, keine Pattern-Vorschläge).

## Begriffe

| Begriff | Definition |
|---------|------------|
| `solid-check` | Analysiert ein SPEC- oder Contract-Artefakt auf SOLID-Verletzungen |
| `pattern-suggest` | Generiert Pattern-Vorschläge für ein Artefakt (ohne Persistenz) |
| `pattern-accept` | Persistiert eine Pattern-Annahme im Register |
| `pattern-reject` | Persistiert eine Pattern-Ablehnung mit Begründung im Register |
| `pattern-list` | Liest und zeigt das Pattern-Register tabellarisch an |

## Gherkin-Szenarien

```gherkin
Feature: SOLID CLI Commands Behavior

  # ── sdd solid-check ──────────────────────────────────────────────────────────

  Scenario: solid-check gibt JSON-Report aus mit --json Flag
    Given SPEC-0015 existiert als draft
    And solid_gate.enabled ist true
    When "sdd solid-check SPEC-0015 --json" ausgeführt wird
    Then ist der Exit-Code 0 oder 1
    And der stdout ist valides JSON
    And das JSON enthält "solid_findings" als Array
    And das JSON enthält "overall_solid_score"

  Scenario: solid-check im warn-Modus gibt Exit-Code 0 bei Violation
    Given solid_gate.mode ist "warn"
    And SPEC-0015 hat mindestens eine SOLID-Violation
    When "sdd solid-check SPEC-0015" ausgeführt wird
    Then ist der Exit-Code 0
    And der Output enthält "[WARN]"

  Scenario: solid-check im block-Modus gibt Exit-Code 1 bei Violation
    Given solid_gate.mode ist "block"
    And SPEC-0015 hat mindestens eine SOLID-Violation mit severity "violation"
    When "sdd solid-check SPEC-0015" ausgeführt wird
    Then ist der Exit-Code 1
    And der Output enthält "violation"

  Scenario: solid-check mit --principle filtert auf ein Prinzip
    Given solid_gate.enabled ist true
    When "sdd solid-check SPEC-0015 --principle S" ausgeführt wird
    Then enthält der Report nur Findings mit principle "S"

  Scenario: solid-check mit unbekannter ID gibt Exit-Code 2
    When "sdd solid-check SPEC-9999" ausgeführt wird
    Then ist der Exit-Code 2
    And der Output enthält "nicht gefunden"

  # ── sdd pattern-suggest ──────────────────────────────────────────────────────

  Scenario: pattern-suggest gibt 1-4 Vorschläge aus
    Given SPEC-0015 existiert
    And pattern_suggestions.enabled ist true
    When "sdd pattern-suggest SPEC-0015" ausgeführt wird
    Then ist der Exit-Code 0
    And der Output enthält mindestens 1 und höchstens 4 Pattern-Vorschläge
    And jeder Vorschlag enthält eine URL die mit "https://refactoring.guru/" beginnt

  Scenario: pattern-suggest ohne Persistenz (nur Ausgabe)
    Given SPEC-0015 existiert
    When "sdd pattern-suggest SPEC-0015" ausgeführt wird
    Then existiert KEINE Datei ".sdd/patterns/SPEC-0015-patterns.json"

  # ── sdd pattern-accept ───────────────────────────────────────────────────────

  Scenario: pattern-accept persistiert Annahme im Register
    Given SPEC-0015 existiert
    When "sdd pattern-accept SPEC-0015 Strategy --reason 'Unabhängige Algorithmen'" ausgeführt wird
    Then ist der Exit-Code 0
    And existiert ".sdd/patterns/SPEC-0015-patterns.json"
    And die Datei enthält pattern_name "Strategy" mit status "accepted"
    And acceptance_reason ist "Unabhängige Algorithmen"

  Scenario: pattern-accept ohne --reason schlägt fehl
    When "sdd pattern-accept SPEC-0015 Strategy" ausgeführt wird
    Then ist der Exit-Code 1
    And der Output enthält "--reason ist erforderlich"

  # ── sdd pattern-reject ───────────────────────────────────────────────────────

  Scenario: pattern-reject persistiert Ablehnung mit Begründung
    Given SPEC-0015 existiert
    When "sdd pattern-reject SPEC-0015 TemplateMethod --reason 'Keine gemeinsame Basis'" ausgeführt wird
    Then ist der Exit-Code 0
    And die Datei ".sdd/patterns/SPEC-0015-patterns.json" enthält pattern_name "TemplateMethod" mit status "rejected"
    And rejection_reason ist "Keine gemeinsame Basis"

  Scenario: pattern-reject ohne --reason schlägt fehl
    When "sdd pattern-reject SPEC-0015 TemplateMethod" ausgeführt wird
    Then ist der Exit-Code 1
    And der Output enthält "--reason ist erforderlich"

  # ── sdd pattern-list ─────────────────────────────────────────────────────────

  Scenario: pattern-list zeigt Tabelle mit Entscheidungen
    Given ".sdd/patterns/SPEC-0015-patterns.json" enthält 2 Einträge
    When "sdd pattern-list SPEC-0015" ausgeführt wird
    Then ist der Exit-Code 0
    And der Output enthält eine Tabelle mit Spalten pattern_name, status, reason

  Scenario: pattern-list ohne Register gibt leere Tabelle (kein Fehler)
    Given ".sdd/patterns/SPEC-0015-patterns.json" existiert nicht
    When "sdd pattern-list SPEC-0015" ausgeführt wird
    Then ist der Exit-Code 0
    And der Output enthält "Keine Pattern-Entscheidungen"
```
