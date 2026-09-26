---
id: CON-0173
project: PRJ-0001
title: "Claude Review-Gate, Retry-Loop und Eskalation"
type: behavior
format: gherkin
spec: SPEC-0045
version: 0.1.0
status: deprecated
artifact: ""
tests: ["TST-0199"]
deprecated_reason: "mit SPEC-0045 abgelöst: Task-Routing durch Rollen-Profile und by_complexity der Pipeline abgelöst (SPEC-0062)"
---

# Contract: Claude Review-Gate, Retry-Loop und Eskalation

> **Spec:** SPEC-0045 · **Typ:** Verhalten (Gherkin) · **Status:** draft

## Zweck

Definiert das beobachtbare Verhalten des Claude-Review-Gates nach dem TDD-Loop,
den Retry-Mechanismus mit Kontext-Anreicherung, und die Eskalation zu Claude
nach Erschöpfung der Retry-Versuche.

## Invarianten

- **INV-01:** Kein Task wird als `completed` markiert ohne Claude-Review — auch bei
  lokalem `pass` des pytest. Bei lokalem pytest `fail` wird Claude **nicht** aufgerufen;
  es folgt direkt der nächste Retry (oder Eskalation wenn max_retries erreicht).
- **INV-02:** Claude bewertet binär: entweder `pass` oder `fail` mit Begründung.
  Eine leere Begründung bei `fail` ist ein Protokollverstoß.
- **INV-03:** Der Retry-Kontext ist akkumulativ: Iteration N enthält alle
  Fehlerbegründungen aus Iterationen 1…N-1.
- **INV-04:** Nach Erreichen von `max_retries` ohne `pass` wird der Task eskaliert
  (nie still verworfen).
- **INV-05:** Ein eskalierter Task wird als `executor: claude (escalated)` markiert
  und über den bestehenden Claude-Code-Gen-Pfad (SPEC-0008 `CodeGenProvider`)
  vollständig neu implementiert — die lokalen Retry-Artefakte werden als Kontext
  mitgeliefert.
- **INV-06:** Prompt Caching: Spec + Contract werden als gecachtes Prefix gesendet
  (`cache_control: {"type": "ephemeral"}`); Diff + Test + pytest-Output sind
  nicht gecacht (pro-Task-Teil).

## Gherkin-Szenarien

```gherkin
Feature: Claude Review-Gate, Retry und Eskalation

  Background:
    Given task_routing.max_retries ist 3
    And Claude Review-Gate ist aktiv für alle local-Tasks

  Scenario: Lokaler pass + Claude pass → Task completed
    Given ein TDD-Loop-Ergebnis mit status "pass"
    When Claude das Ergebnis reviewed (Diff + Test + pytest-Output)
    And Claude bewertet "pass"
    Then wird der Task-Status auf "completed" gesetzt
    And executor bleibt "local"

  Scenario: Lokaler pass + Claude fail → Retry
    Given ein TDD-Loop-Ergebnis mit status "pass" in Iteration 1
    When Claude bewertet "fail" mit Begründung "Contract-Invariante INV-02 verletzt"
    Then startet Iteration 2 mit ursprünglichem Kontext + Claudes Begründung
    And der akkumulierte Kontext enthält die Begründung aus Iteration 1

  Scenario: Kontext-Akkumulation über Iterationen
    Given Iteration 1 fail-Begründung: "Test fehlt Edge-Case"
    And Iteration 2 fail-Begründung: "Implementierung ignoriert Timeout"
    When Iteration 3 startet
    Then enthält der Retry-Kontext beide Begründungen aus Iteration 1 und 2

  Scenario: Eskalation nach max_retries
    Given 3 Iterationen ohne Claude-pass
    When die Retry-Anzahl max_retries (3) erreicht ist
    Then wird der Task eskaliert
    And executor wird auf "claude (escalated)" gesetzt
    And der akkumulierte Kontext aus 3 Iterationen wird an Claude übergeben
    And Claude implementiert den Task vollständig via get_code_gen_provider()

  Scenario: Kein completed ohne Claude-Review
    Given ein Task bei dem pytest "pass" zurückgibt
    And das Claude-Review ist nicht erreichbar (Timeout)
    When der Task-Loop endet
    Then ist der Task-Status nicht "completed"
    And ein Fehler wird geloggt

  Scenario: Prompt-Caching-Prefix bleibt warm
    Given ein sdd-implement-Lauf mit 5 local-Tasks
    When Claude die Tasks der Reihe nach reviewed (synchron in max_concurrent-Gruppen)
    Then wird Spec + Contract als cache_control:ephemeral-Prefix genau einmal gesendet
    And alle nachfolgenden Reviews nutzen den Cache-Hit

  Scenario: Lokaler pytest fail → kein Claude-Review, direkt Retry
    Given ein TDD-Loop-Ergebnis mit status "fail" (pytest exit-code != 0) in Iteration 1
    When der Loop-Controller das Ergebnis auswertet
    Then wird Claude NICHT aufgerufen
    And Iteration 2 startet direkt mit dem Fehler-Output als Retry-Kontext

  Scenario: Claude pass bei Task aus Eskalations-Pfad
    Given ein Task mit executor "claude (escalated)"
    When Claude den Task implementiert und pytest besteht
    Then wird der Task-Status auf "completed" gesetzt
    And executor bleibt "claude (escalated)"
```
