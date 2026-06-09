---
id: CON-0158
project: ""
title: "HOL-Datei-Struktur und Idempotenz-Garantie"
type: behavior
format: gherkin
spec: SPEC-0033
version: 0.1.0
status: approved
artifact: ".sdd/contracts/behavior/hol-datei-struktur-und-idempotenz-garantie.feature"
tests: ["TST-0184"]
---

# Contract: HOL-Datei-Struktur und Idempotenz-Garantie

> **Spec:** SPEC-0033 · **Typ:** Verhalten (Gherkin) · **Status:** review

## Zweck

Legt fest welche Felder eine von `sdd generate-holdouts` erzeugte HOL-Datei
enthalten muss und garantiert dass mehrfaches Ausführen keine Duplikate erzeugt.

## Garantien

Die im Artifact hinterlegten Szenarien sind **ausführbare Spezifikation**.

## Invarianten

- **INV-01:** Jede HOL-Datei besitzt ein YAML-Frontmatter mit `id`, `spec`, `status`, `title`.
- **INV-02:** `status` ist immer `ready` bei neu generierten Holdouts.
- **INV-03:** Der Body enthält die Abschnitte `## Input`, `## Expected`, `## Evaluation Hint`.
- **INV-04:** Ein zweiter Aufruf für dieselbe Spec erzeugt keine neuen HOL-Dateien wenn bereits HOL-Dateien für alle Contracts existieren.

## Begriffe

| Begriff          | Definition                                                      |
|------------------|-----------------------------------------------------------------|
| Pflichtfelder    | `id`, `spec`, `status`, `title` im YAML-Frontmatter            |
| Evaluation Hint  | Aufzählung konkreter Prüfpunkte die der Evaluator abarbeitet   |

## Szenarien

```gherkin
Feature: HOL-Datei-Struktur

  Scenario: Erzeugte HOL-Datei enthält alle Pflichtfelder
    Given `sdd generate-holdouts SPEC-0033` wurde erfolgreich ausgeführt
    When eine der erzeugten HOL-Dateien gelesen wird
    Then enthält das Frontmatter die Felder: id, spec, status, title
    And status ist "ready"
    And spec ist "SPEC-0033"
    And der Body enthält den Abschnitt "## Input"
    And der Body enthält den Abschnitt "## Expected"
    And der Body enthält den Abschnitt "## Evaluation Hint"

  Scenario: Zweiter Aufruf erzeugt keine Duplikate
    Given `sdd generate-holdouts SPEC-0033` wurde bereits ausgeführt
    And N HOL-Dateien für SPEC-0033 existieren
    When der Nutzer `sdd generate-holdouts SPEC-0033` erneut ausführt
    Then endet der Befehl mit Exit-Code 0
    And die Anzahl der HOL-Dateien für SPEC-0033 ist immer noch N
    And die Ausgabe enthält "N Holdouts übersprungen (bereits vorhanden)"

  Scenario: HOL-ID ist eindeutig und sequenziell
    Given keine HOL-Dateien für SPEC-0033 existieren
    When `sdd generate-holdouts SPEC-0033` ausgeführt wird und 3 HOL-Dateien erzeugt
    Then haben alle 3 Dateien unterschiedliche IDs im Format HOL-XXXX
    And keine ID existiert bereits in .sdd/holdout/
```
