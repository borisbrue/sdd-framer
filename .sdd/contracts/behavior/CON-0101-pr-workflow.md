---
id: CON-0101
title: "PR-Workflow – Branch, Commits, Tests, Merge und Spec-Abschluss"
type: behavior
format: gherkin
spec: SPEC-0026
version: 0.1.0
status: deprecated
artifact: "contracts/behavior/pr-workflow.feature"
tests:
- TST-0120
deprecated_reason: "mit SPEC-0026 abgelöst: Distribution Engine ohne Codeerzeugung; abgelöst durch die Rollen-Pipeline"
---

# Contract: PR-Workflow – Branch, Commits, Tests, Merge und Spec-Abschluss

> **Spec:** SPEC-0026 · **Typ:** Verhalten (Gherkin) · **Status:** draft

## Zweck

Legt den vollständigen End-to-End-Ablauf von der Branch-Erstellung bis zum
Spec-Abschluss fest (FR-06/12–16). Dieser Contract beschreibt das Verhalten
des `SddOrchestrator` auf der höchsten Abstraktionsebene.

## Garantien

- Pro Spec wird genau ein Branch `spec/SPEC-XXXX` angelegt.
- Jeder `committed` Task erzeugt genau einen Commit auf dem Spec-Branch.
- PR wird erst erstellt wenn alle Tasks entweder `committed` oder `blocked` sind.
- Blockierte Tasks werden im PR-Body aufgelistet und erfordern manuelle Entscheidung.
- Nach grünen Tests wird PR automatisch in `main` gemergt.
- Spec-Status wechselt auf `implemented` nach erfolgreichem Merge.
- Alle Container des Specs werden nach Merge entfernt (CON-0099).

## Invarianten

- **INV-01:** Branch `spec/SPEC-XXXX` existiert genau einmal pro Spec-Ausführung.
- **INV-02:** Kein Merge ohne grüne Test-Suite.
- **INV-03:** Spec-Status `implemented` wird nur nach Merge gesetzt, nie vorher.
- **INV-04:** Hat ein Spec ausschließlich blockierte Tasks (0 commits), wird kein PR erstellt.

## Szenarien (Gherkin)

```gherkin
Feature: PR-Workflow

  Scenario: Alle Tasks committed – vollständiger Happy Path
    Given Spec SPEC-0026 mit 8 Tasks, alle status="committed"
    When orchestrator.finalize(SPEC-0026) aufgerufen wird
    Then existiert Branch "spec/SPEC-0026" mit 8 Commits
    And ein PR "LLM Task Distribution Engine" wird gegen main erstellt
    And die Test-Suite läuft auf dem PR
    When Tests: passed
    Then wird der PR in main gemergt
    And SPEC-0026.status == "implemented"
    And alle Container des Specs sind entfernt

  Scenario: Teilweise blockierte Tasks – PR mit Warnung
    Given SPEC-0026 mit 6 committed + 2 blocked Tasks
    When orchestrator.finalize(SPEC-0026) aufgerufen wird
    Then wird ein PR erstellt
    And der PR-Body listet die 2 blockierten Tasks
    And Entwickler muss manuell entscheiden (kein Auto-Merge)

  Scenario: Nur blockierte Tasks – kein PR
    Given SPEC-0026 mit 0 committed + 5 blocked Tasks
    When orchestrator.finalize(SPEC-0026) aufgerufen wird
    Then wird kein PR erstellt (INV-04)
    And Entwickler erhält Fehlermeldung mit allen blockierten Tasks

  Scenario: Tests schlagen fehl – kein Merge
    Given ein PR für SPEC-0026
    When Test-Suite fehlschlägt
    Then wird der PR nicht gemergt (INV-02)
    And SPEC-0026.status bleibt auf "in-progress"
    And Entwickler wird benachrichtigt

  Scenario: Cleanup nach Merge
    Given alle Container C1, C2, C3 für SPEC-0026
    When PR erfolgreich gemergt
    Then werden C1, C2, C3 entfernt
    And kein Container mit SPEC-0026-Bezug existiert mehr
```

## Begriffe

| Begriff | Definition |
|---|---|
| Spec-Branch | `spec/SPEC-XXXX` – dedizierter Branch für alle Task-Commits |
| Auto-Merge | Merge ohne manuellen Eingriff bei 100% committed + grünen Tests |
| Blocked-PR | PR mit blockierten Tasks – erfordert Entwickler-Entscheidung |
