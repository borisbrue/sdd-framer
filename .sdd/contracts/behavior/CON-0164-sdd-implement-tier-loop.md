---
id: CON-0164
project: PRJ-0001
title: "sdd-implement Schritt 5.5: Tier-spezifische Loop-Verzweigung"
type: behavior
format: markdown
spec: SPEC-0042
version: 0.1.0
status: deprecated
artifact: "contracts/behavior/sdd-implement-tier-loop.md"
tests:
- TST-0192
deprecated_reason: "Holdout-Stufen laufen im Pipeline-Schritt holdout (SPEC-0062, CON-0216)"
---

# Contract: sdd-implement Schritt 5.5 — Tier-spezifische Loop-Verzweigung

> **Spec:** SPEC-0042 · **Typ:** Verhalten · **Status:** draft

## Zweck

Definiert das Verhalten von sdd-implement.md Schritt 5.5 nach Einarbeitung
des tier-spezifischen Loops gemäß SPEC-0042.

## Der Loop

```
sdd implement (Tasks ausführen)
       ↓
Schritt 1b: docker build → Container starten
       ↓
Schritt 5.5a: sdd evaluate --spec ID --tier critical --output-json
       ↓ fail                              ↓ pass
tier_summary.critical.failed > 0          Schritt 5.5b: --tier normal --output-json
→ task_delta aus Report lesen                  ↓ fail                ↓ pass
→ 1–2 Tasks patchen                       task_delta lesen    Schritt 5.5c: --tier edge-case
→ zurück zu Schritt 1b                    Tasks patchen            ↓ fail       ↓ pass
  (Container neu starten)                 → sdd evaluate        task_delta    ✓ Schritt 6
                                            alle Tiers           Tasks patchen
                                                              → sdd evaluate alle Tiers
```

## Verhalten des Skill-Prompts (Schritt 5.5)

| Situation                          | Aktion des Agents                                               |
|------------------------------------|-----------------------------------------------------------------|
| critical tier_summary.failed > 0   | `task_delta` lesen; max. 2 Tasks patchen; Container neu starten (Schritt 1b); nur critical re-evaluieren |
| normal tier_summary.failed > 0     | `task_delta` lesen; Tasks patchen; alle Tiers re-evaluieren    |
| edge-case tier_summary.failed > 0  | `task_delta` lesen; Tasks patchen; alle Tiers re-evaluieren    |
| alle Tiers passed                  | weiter zu Schritt 6 (sdd finalize)                             |

## Invarianten

- Bei critical-Fehler: Container wird **immer** neu gestartet (nicht nur Code patchen)
- `task_delta` wird **immer** zuerst gelesen bevor neue Code-Analyse beginnt
- Maximale Retries pro Tier: 3 (danach `--final-attempt` und Abbruch)
- Der Agent liest `.sdd/holdout/`-Dateien **niemals** direkt (Isolation bleibt erhalten)

## Gherkin

```gherkin
Feature: sdd-implement tier-spezifischer Holdout-Loop

  Scenario: Critical-Fehler löst Container-Neustart aus
    Given alle Tasks sind grün (Schritt 4 abgeschlossen)
    When Schritt 5.5a läuft und ein critical-Holdout schlägt fehl
    Then liest der Agent task_delta aus dem JSON-Report
    And patcht maximal 2 Tasks
    And startet den Container neu (Schritt 1b)
    And führt danach nur --tier critical erneut aus

  Scenario: Normal-Fehler patcht Tasks ohne Container-Neustart
    Given critical Tiers bestehen
    When Schritt 5.5b läuft und ein normal-Holdout schlägt fehl
    Then liest der Agent task_delta aus dem JSON-Report
    And patcht die betroffenen Tasks
    And führt sdd evaluate (alle Tiers) erneut aus
    And startet den Container NICHT neu

  Scenario: Alle Tiers bestehen → Schritt 6
    Given critical, normal und edge-case bestehen
    When Schritt 5.5c abgeschlossen ist
    Then ruft der Agent sdd finalize auf
```
