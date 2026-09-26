---
id: CON-0113
title: "/sdd-implement – Vollständiger Auto-Flow (start → branch → decompose → TDD → finalize)"
type: behavior
format: gherkin
spec: SPEC-0029
version: 0.1.0
status: deprecated
artifact: "contracts/behavior/sdd-implement-auto-flow.feature"
tests:
- TST-0132
deprecated_reason: "/sdd-implement läuft über sdd pipeline run (SPEC-0062, CON-0216)"
---

# Contract: /sdd-implement – Vollständiger Auto-Flow

> **Spec:** SPEC-0029 · **Typ:** Verhalten (Gherkin) · **Status:** draft

## Zweck

Stellt sicher, dass `/sdd-implement SPEC-XXXX` den gesamten Implementierungsflow
eigenständig orchestriert: `sdd start`, Feature-Branch-Erstellung, Decompose-Plan
als Implementierungsreihenfolge, TDD-Zyklus pro Task und `sdd finalize`.
`sdd finalize` startet keinen Container selbst; beim dritten fehlgeschlagenen
Finalize-Versuch wird `--skip-container` vorgeschlagen.

## Garantien

- `sdd start SPEC-XXXX` wird automatisch ausgeführt wenn Status noch nicht `in-progress`
- Ein Feature-Branch `feat/SPEC-XXXX` wird erstellt oder ausgecheckt (nie Fehler wenn bereits vorhanden)
- `sdd decompose SPEC-XXXX` wird geladen und als sequenzieller Implementierungsplan genutzt
- Der TDD-Zyklus läuft Task für Task aus dem Decompose-Plan
- `sdd finalize SPEC-XXXX` wird am Ende aufgerufen; bricht mit explizitem Fehler ab wenn kein Container läuft
- Beim dritten fehlgeschlagenen Finalize-Versuch schlägt der Skill `sdd finalize SPEC-XXXX --skip-container` vor
- `sdd finalize --skip-container` überspringt Container-Check und Testlauf; Commit und PR laufen normal; Warnung wird ausgegeben

## Invarianten

- **INV-01:** Der Skill liest niemals `.sdd/holdout/` — evaluator isolation gilt unverändert.
- **INV-02:** `sdd finalize` startet keinen Container; der Container muss bereits laufen.
- **INV-03:** `--skip-container` erfordert explizite Nutzerbestätigung bevor es ausgeführt wird.
- **INV-04:** Decompose-Tasks werden als Plan geladen, nicht an den LLM-Pool verteilt (`sdd distribute` bleibt `sdd orchestrate` vorbehalten).

## Szenarien (Gherkin)

```gherkin
Feature: /sdd-implement – Auto-Flow

  Scenario: Happy Path – Spec approved, Container läuft
    Given SPEC-XXXX hat status: approved
    And alle Contracts von SPEC-XXXX sind approved
    And Test-Stubs existieren
    And der Dev-Container für SPEC-XXXX läuft
    When /sdd-implement SPEC-XXXX aufgerufen wird
    Then wird sdd start SPEC-XXXX ausgeführt (Status → in-progress)
    And Branch "feat/SPEC-XXXX" wird erstellt oder ausgecheckt
    And sdd decompose SPEC-XXXX wird als Implementierungsplan geladen (INV-04)
    And der TDD-Zyklus wird Task für Task ausgeführt
    And sdd finalize SPEC-XXXX wird am Ende aufgerufen

  Scenario: Branch existiert bereits
    Given Branch "feat/SPEC-XXXX" existiert bereits
    When /sdd-implement SPEC-XXXX den Branch-Schritt ausführt
    Then wird auf "feat/SPEC-XXXX" ausgecheckt ohne Fehler

  Scenario: Container läuft nicht beim Finalize
    Given SPEC-XXXX ist in-progress
    And kein Dev-Container für SPEC-XXXX läuft
    When sdd finalize SPEC-XXXX aufgerufen wird
    Then erscheint "✗ Dev-Container nicht gefunden – starte ihn mit 'sdd start SPEC-XXXX'"
    And der Exit-Code ist 1 (INV-02)

  Scenario: Dritter fehlgeschlagener Finalize-Versuch
    Given sdd finalize ist bereits 2x mit Container-Fehler fehlgeschlagen
    When /sdd-implement den dritten Finalize-Versuch vorbereitet
    Then schlägt der Skill vor: "sdd finalize SPEC-XXXX --skip-container"
    And wartet auf explizite Bestätigung (INV-03)
    And nach Bestätigung laufen Commit und PR ohne Container-Testlauf
    And erscheint "⚠ Container-Tests wurden übersprungen"

  Scenario: Decompose liefert leere Task-Liste
    Given sdd decompose SPEC-XXXX liefert 0 Tasks
    When /sdd-implement den Decompose-Schritt ausführt
    Then erscheint "✗ Keine Tasks gefunden – prüfe Spec-Inhalt"
    And der Flow stoppt

  Scenario: sdd start schlägt fehl wegen ungültigem Status
    Given SPEC-XXXX hat status: deprecated
    When /sdd-implement SPEC-XXXX aufgerufen wird
    Then erscheint "✗ Spec hat Status 'deprecated' – Implementierung nicht möglich"
    And der Flow stoppt ohne Branch oder Code zu erstellen

  Scenario: Holdout bleibt isoliert
    Given ".sdd/holdout/" enthält Evaluierungsszenarien
    When /sdd-implement SPEC-XXXX ausgeführt wird
    Then wird ".sdd/holdout/" zu keinem Zeitpunkt gelesen (INV-01)
```

## Begriffe

| Begriff | Definition |
|---|---|
| Decompose-Plan | Output von `sdd decompose SPEC-XXXX` — Liste klassifizierter Tasks als Implementierungsreihenfolge |
| `--skip-container` | Flag für `sdd finalize` das Container-Check und Testlauf überspringt; Commit/PR laufen normal |
| TDD-Zyklus | Schreiben → Testen im Container → Korrigieren bis alle Tests grün |
| Template Method | Fixes Skelett (start→branch→decompose→TDD→finalize) mit anpassbaren Einzelschritten |
