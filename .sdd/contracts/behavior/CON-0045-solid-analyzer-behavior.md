---
id: CON-0045
project: PRJ-0001
title: "SOLID Analyzer Behavior"
type: behavior
format: gherkin
spec: SPEC-0015
version: 0.1.0
status: review
artifact: ".sdd/contracts/behavior/solid-analyzer-behavior.feature"
tests: ["TST-0001"]
---

# Contract: SOLID Analyzer Behavior

> **Spec:** SPEC-0015 · **Typ:** Verhalten (Gherkin) · **Status:** review

## Zweck

Definiert das beobachtbare Verhalten des `SolidAnalyzer` bei der Prüfung von
SPECs und Contracts gegen die 5 SOLID-Prinzipien. Jeder der 5 Checker
(SrpChecker, OcpChecker, LspChecker, IspChecker, DipChecker) folgt dem
Strategy-Pattern und gibt eine strukturierte Finding-Liste zurück.

## Garantien

Die im Artifact hinterlegten Szenarien sind **ausführbare Spezifikation**.
Jedes Szenario MUSS durch einen automatisierten Test abgedeckt sein.

## Invarianten

- **INV-01:** Jedes Finding enthält `principle` ∈ {S, O, L, I, D}, `severity` ∈ {info, warn, violation}, `location` (nicht leer), `description` (nicht leer), `suggestion`.
- **INV-02:** `overall_solid_score` ∈ {compliant, warn, violation}. Ist mindestens ein Finding mit `severity: violation` vorhanden, ist der Score `violation`.
- **INV-03:** Ein deaktivierter Checker (NullSolidChecker) gibt immer eine leere Finding-Liste zurück und ändert den Score nicht.
- **INV-04:** Die Checker-Kette läuft vollständig durch – ein Checker-Fehler unterbricht nicht die Kette, sondern wird als Finding mit `severity: info` und `principle: S` protokolliert.
- **INV-05:** Der LLM-Aufruf pro Checker ist idempotent bei gleichem Artefakt-Inhalt (gecachte Ergebnisse werden für dasselbe Content-Hash wiederverwendet, wenn Caching aktiviert).

## Begriffe

| Begriff | Definition |
|---------|------------|
| `SolidChecker` | Protocol/Interface; eine Implementierung prüft genau ein SOLID-Prinzip |
| `SolidAnalyzer` | Orchestriert eine geordnete Liste von `SolidChecker`-Instanzen (Chain of Responsibility) |
| `NullSolidChecker` | Gibt immer `[]` zurück; wird verwendet wenn `solid_gate.enabled: false` |
| `SolidFinding` | Ein einzelnes Ergebnis einer Prüfung: principle, severity, location, description, suggestion |
| `SolidReport` | Aggregiertes Ergebnis aller Checker: findings[], overall_solid_score, summary |
| `artifact` | SPEC oder Contract, der analysiert wird |

## Gherkin-Szenarien

```gherkin
Feature: SOLID Analyzer Behavior

  Background:
    Given der SolidAnalyzer ist mit allen 5 Checkern (S, O, L, I, D) konfiguriert
    And solid_gate.enabled ist true

  Scenario: Konformes Artefakt erhält Score 'compliant'
    Given ein SPEC-Artefakt ohne erkennbare SOLID-Violations
    When der SolidAnalyzer das Artefakt analysiert
    Then ist overall_solid_score "compliant"
    And die findings-Liste ist leer oder enthält nur severity "info"

  Scenario: SRP-Violation wird als 'violation' gemeldet
    Given ein SPEC-Artefakt, das zwei unabhängige fachliche Domänen beschreibt
    When der SrpChecker das Artefakt analysiert
    Then enthält findings mindestens ein Eintrag mit principle "S" und severity "violation"
    And der Eintrag enthält ein nicht-leeres "location"-Feld
    And der Eintrag enthält ein nicht-leeres "suggestion"-Feld
    And overall_solid_score ist "violation"

  Scenario: OCP-Warnung bei fehlendem Erweiterungspunkt
    Given ein Contract-Artefakt ohne beschriebene Erweiterungsschnittstellen
    When der OcpChecker das Artefakt analysiert
    Then enthält findings mindestens ein Eintrag mit principle "O" und severity "warn" oder "violation"

  Scenario: NullSolidChecker liefert immer leeres Ergebnis
    Given solid_gate.enabled ist false
    And der SolidAnalyzer verwendet NullSolidChecker für alle Prinzipien
    When der SolidAnalyzer ein beliebiges Artefakt analysiert
    Then ist die findings-Liste leer
    And overall_solid_score ist "compliant"

  Scenario: Checker-Fehler unterbricht Kette nicht
    Given der IspChecker wirft eine RuntimeError-Exception
    When der SolidAnalyzer das Artefakt analysiert
    Then werden die verbleibenden Checker (D) trotzdem ausgeführt
    And findings enthält einen Eintrag mit principle "I", severity "info", description enthält "Checker-Fehler"

  Scenario: Score 'violation' wenn mindestens ein violation-Finding vorhanden
    Given findings enthält [severity "warn", severity "violation", severity "info"]
    When overall_solid_score berechnet wird
    Then ist overall_solid_score "violation"

  Scenario: Score 'warn' wenn nur warn-Findings, kein violation
    Given findings enthält [severity "warn", severity "info"]
    When overall_solid_score berechnet wird
    Then ist overall_solid_score "warn"
```
