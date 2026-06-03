---
id: CON-0124
project: ""
title: "Task-Completion-Gate – Testpflicht vor passed-Transition"
type: behavior
format: gherkin
spec: SPEC-0034
version: 0.1.0
status: draft
artifact: ".sdd/contracts/behavior/task-completion-gate-behavior.feature"
tests: ["TST-0145", "TST-0146"]
---

# Contract: Task-Completion-Gate

> **Spec:** SPEC-0034 · **Typ:** Verhalten (Gherkin) · **Status:** draft

## Geltungsbereich

Dieser Contract gilt für die `mark_passed()`-Transition in `TaskLifecycle`
(SPEC-0026, `task_lifecycle.py`). Er erweitert den bestehenden `TaskLifecycle`
um eine obligatorische Test-Ausführung vor der `passed`-Transition.

## Zweck

Beschreibt das beobachtbare Verhalten des Task-Completion-Gates:
- Ein Task darf nur nach `passed` wechseln wenn alle `test_ids` grün sind (FR-04/FR-05)
- `test_ids = []` blockiert die `passed`-Transition mit einer Warnung (FR-05)
- Fehlgeschlagene Tests hinterlassen die Fehlermeldung in `error_context`

## Garantien

```gherkin
Feature: Task-Completion-Gate

  Background:
    Given ein TaskLifecycle mit einem Task im Status "review"

  Scenario: Passed-Transition mit grünem Test
    Given der Task hat test_ids=["TST-0001"]
    And TST-0001 läuft erfolgreich durch
    When mark_passed() aufgerufen wird
    Then wechselt der Task-Status zu "passed"
    And error_context bleibt leer

  Scenario: Passed-Transition mit fehlgeschlagenem Test
    Given der Task hat test_ids=["TST-0001"]
    And TST-0001 schlägt fehl mit "AssertionError: expected 200, got 500"
    When mark_passed() aufgerufen wird
    Then wechselt der Task-Status zu "failed"
    And error_context enthält "AssertionError: expected 200, got 500"

  Scenario: Passed-Transition ohne test_ids – blockiert
    Given der Task hat test_ids=[]
    When mark_passed() aufgerufen wird
    Then wird TestRequiredError ausgelöst
    And der Task-Status bleibt "review"
    And error_context enthält "Kein Test zugewiesen – mark_passed() blockiert"

  Scenario: Passed-Transition mit mehreren Tests – alle müssen grün sein
    Given der Task hat test_ids=["TST-0001", "TST-0002"]
    And TST-0001 läuft erfolgreich
    And TST-0002 schlägt fehl mit "TimeoutError"
    When mark_passed() aufgerufen wird
    Then wechselt der Task-Status zu "failed"
    And error_context enthält "TimeoutError"

  Scenario: Passed-Transition mit mehreren Tests – alle grün
    Given der Task hat test_ids=["TST-0001", "TST-0002"]
    And beide Tests laufen erfolgreich durch
    When mark_passed() aufgerufen wird
    Then wechselt der Task-Status zu "passed"

```

> **Hinweis:** Zirkuläre-Dependency-Erkennung beim Decompose ist in CON-0097 spezifiziert,
> nicht hier. CON-0124 gilt ausschließlich für die `mark_passed()`-Transition.

## Invarianten

- INV-01: `mark_passed()` ohne vorherige Testausführung ist ein Fehler (`TestRequiredError`)
- INV-02: Alle Tests in `test_ids` müssen erfolgreich sein — partial pass ist nicht erlaubt
- INV-03: Der `error_context` enthält die originale Fehlermeldung des fehlgeschlagenen Tests
- INV-04: Zirkuläre Dependencies werden in `O(n²)` erkannt (DFS mit Visited-Set)
