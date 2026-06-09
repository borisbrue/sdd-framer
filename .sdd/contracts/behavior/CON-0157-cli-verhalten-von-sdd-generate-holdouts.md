---
id: CON-0157
project: ""
title: "CLI-Verhalten von sdd generate-holdouts"
type: behavior
format: gherkin
spec: SPEC-0033
version: 0.1.0
status: approved
artifact: ".sdd/contracts/behavior/cli-verhalten-von-sdd-generate-holdouts.feature"
tests: ["TST-0183"]
---

# Contract: CLI-Verhalten von sdd generate-holdouts

> **Spec:** SPEC-0033 · **Typ:** Verhalten (Gherkin) · **Status:** review

## Zweck

Legt das beobachtbare CLI-Verhalten von `sdd generate-holdouts SPEC-XXXX` fest:
welche Eingaben akzeptiert werden, was im Erfolgsfall ausgegeben wird und welche
Fehlermeldungen bei ungültigen Vorbedingungen erscheinen.

## Garantien

Die im Artifact hinterlegten Szenarien sind **ausführbare Spezifikation**.

## Invarianten

- **INV-01:** Der Befehl liest niemals `tool/`, `web/`, `tests/`, `*.py`, `*.ts` — nur Spec und Contracts.
- **INV-02:** Ohne explizites `--force` werden bestehende HOL-Dateien nicht überschrieben.
- **INV-03:** Exit-Code 0 bei Erfolg (auch wenn 0 neue HOL-Dateien erzeugt wurden), Exit-Code 1 bei Fehler.

## Begriffe

| Begriff    | Definition                                                    |
|------------|---------------------------------------------------------------|
| HOL-Datei  | Markdown-Datei unter `.sdd/holdout/` mit Holdout-Szenario    |
| Contract   | Datei unter `.sdd/contracts/` die in `contracts:` der Spec steht |

## Szenarien

```gherkin
Feature: sdd generate-holdouts CLI

  Scenario: Happy Path – Holdouts für Spec mit Contracts generieren
    Given eine Spec "SPEC-0033" mit status "approved" und 2 verlinkten Contracts
    And keine HOL-Dateien für SPEC-0033 existieren
    When der Nutzer `sdd generate-holdouts SPEC-0033` ausführt
    Then endet der Befehl mit Exit-Code 0
    And die Ausgabe enthält mindestens 4 HOL-IDs (2 pro Contract)
    And die Ausgabe zeigt "N Holdouts angelegt" mit N >= 4

  Scenario: Spec mit status draft wird abgelehnt
    Given eine Spec "SPEC-0033" mit status "draft"
    When der Nutzer `sdd generate-holdouts SPEC-0033` ausführt
    Then endet der Befehl mit Exit-Code 1
    And die Ausgabe enthält "Spec muss approved oder in-progress sein"
    And es werden keine Dateien geschrieben

  Scenario: Spec ohne Contracts wird abgelehnt
    Given eine Spec "SPEC-0033" mit status "approved" und leerer contracts-Liste
    When der Nutzer `sdd generate-holdouts SPEC-0033` ausführt
    Then endet der Befehl mit Exit-Code 1
    And die Ausgabe enthält "Keine Contracts gefunden"
    And es werden keine Dateien geschrieben

  Scenario: Unbekannte Spec-ID
    Given keine Spec-Datei mit ID "SPEC-9999" existiert
    When der Nutzer `sdd generate-holdouts SPEC-9999` ausführt
    Then endet der Befehl mit Exit-Code 1
    And die Ausgabe enthält "Spec SPEC-9999 nicht gefunden"
```
