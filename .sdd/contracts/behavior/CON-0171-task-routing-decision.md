---
id: CON-0171
project: PRJ-0001
title: "Task-Routing-Entscheidung – complexity_score → executor"
type: behavior
format: gherkin
spec: SPEC-0045
version: 0.1.0
status: deprecated
artifact: ""
tests: ["TST-0197"]
deprecated_reason: "mit SPEC-0045 abgelöst: Task-Routing durch Rollen-Profile und by_complexity der Pipeline abgelöst (SPEC-0062)"
---

# Contract: Task-Routing-Entscheidung

> **Spec:** SPEC-0045 · **Typ:** Verhalten (Gherkin) · **Status:** draft

## Zweck

Definiert das beobachtbare Verhalten der Routing-Entscheidung: welcher Executor
(local LLM oder Claude) für einen Task gewählt wird, basierend auf `complexity_score`
und Systemkonfiguration.

## Invarianten

- **INV-01:** Jeder Task erhält nach der Decomposition genau einen `complexity_score`
  (integer, 0–100 inklusive).
- **INV-02:** Das `executor`-Feld eines Tasks ist nach der Routing-Entscheidung immer
  gesetzt (niemals `None`); erlaubte Werte: `local`, `claude`.
- **INV-03:** Ist `task_routing.enabled: false` oder ist `llm.local_llm` nicht
  konfiguriert, wird immer `executor: claude` gesetzt — unabhängig vom Score.
- **INV-04:** Der Schwellenwert-Vergleich ist `≤` (inklusiv): Score gleich Threshold
  → `executor: local`.
- **INV-05:** Die Routing-Entscheidung ist deterministisch für denselben Score und
  dieselbe Konfiguration.

## Gherkin-Szenarien

```gherkin
Feature: Task-Routing-Entscheidung

  Background:
    Given task_routing.enabled ist true
    And llm.local_llm ist konfiguriert (provider: openai-compat)
    And task_routing.complexity_threshold ist 30

  Scenario: Trivialer Task wird lokal ausgeführt
    Given ein Task mit complexity_score 20
    When die Routing-Entscheidung getroffen wird
    Then ist executor "local"

  Scenario: Task genau am Schwellenwert wird lokal ausgeführt
    Given ein Task mit complexity_score 30
    When die Routing-Entscheidung getroffen wird
    Then ist executor "local"

  Scenario: Komplexer Task wird an Claude delegiert
    Given ein Task mit complexity_score 31
    When die Routing-Entscheidung getroffen wird
    Then ist executor "claude"

  Scenario: Routing deaktiviert – immer Claude
    Given task_routing.enabled ist false
    And ein Task mit complexity_score 5
    When die Routing-Entscheidung getroffen wird
    Then ist executor "claude"

  Scenario: llm.local_llm nicht konfiguriert – immer Claude
    Given llm.local_llm ist nicht in config.yaml vorhanden
    And task_routing.enabled ist true
    And ein Task mit complexity_score 10
    When die Routing-Entscheidung getroffen wird
    Then ist executor "claude"

  Scenario: complexity_score Untergrenze
    Given ein Task mit complexity_score 0
    When die Routing-Entscheidung getroffen wird
    Then ist executor "local"

  Scenario: complexity_score Obergrenze
    Given ein Task mit complexity_score 100
    When die Routing-Entscheidung getroffen wird
    Then ist executor "claude"

  Scenario: Ungültiger complexity_score wirft Fehler
    Given ein Task mit complexity_score -1
    When die Routing-Entscheidung getroffen wird
    Then wird ValueError geworfen mit Hinweis auf erlaubten Bereich 0–100
```
