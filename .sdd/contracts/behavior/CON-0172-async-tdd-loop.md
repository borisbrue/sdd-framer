---
id: CON-0172
project: PRJ-0001
title: "Async TDD-Loop – test → implement → pytest (LocalLLMExecutor)"
type: behavior
format: gherkin
spec: SPEC-0045
version: 0.1.0
status: deprecated
artifact: ""
tests: ["TST-0198"]
deprecated_reason: "mit SPEC-0045 abgelöst: Task-Routing durch Rollen-Profile und by_complexity der Pipeline abgelöst (SPEC-0062)"
---

# Contract: Async TDD-Loop

> **Spec:** SPEC-0045 · **Typ:** Verhalten (Gherkin) · **Status:** draft

## Zweck

Definiert den Pflichtablauf des lokalen TDD-Loops: Test schreiben → Implementieren →
pytest ausführen. Der Loop läuft als asyncio-Coroutine; mehrere unabhängige Tasks
können gleichzeitig ausgeführt werden.

## Invarianten

- **INV-01:** Der Test muss vor der Implementierung existieren. Eine Implementierung
  ohne vorherigen Test ist ein Protokollverstoß.
- **INV-02:** Die Testdatei liegt immer unter `tests/unit/test_<task_id>.py`.
- **INV-03:** pytest wird via `asyncio.create_subprocess_exec` aufgerufen — kein
  blocking `subprocess.run` im Event-Loop-Thread.
- **INV-04:** Das Ergebnis eines Loop-Durchlaufs enthält immer: `pass|fail`,
  pytest-stdout, pytest-returncode, Iterationsnummer.
- **INV-05:** Maximal `task_routing.max_concurrent` Tasks laufen gleichzeitig
  (Semaphore). Überschuss wartet in einer Queue.
- **INV-06:** Der LLM-Aufruf erfolgt via `get_completion_provider(config, "local_llm")`
  (SPEC-0008 Factory) — kein direkter HTTP-Call im Executor.

## Gherkin-Szenarien

```gherkin
Feature: Async TDD-Loop

  Background:
    Given llm.local_llm ist konfiguriert
    And task_routing.max_concurrent ist 3
    And ein Task mit executor "local" und task_id "TSK-001"

  Scenario: Erfolgreicher erster Versuch
    Given das lokale LLM schreibt einen validen Test (tests/unit/test_TSK-001.py)
    And das lokale LLM schreibt eine Implementierung die den Test besteht
    When der TDD-Loop für TSK-001 ausgeführt wird
    Then existiert tests/unit/test_TSK-001.py vor der Implementierungsdatei
    And pytest gibt exit-code 0 zurück
    And das Loop-Ergebnis enthält status "pass", iteration 1

  Scenario: Test existiert vor Implementierung (Pflicht-Invariante)
    Given das LLM liefert Test und Implementierung in einem Schritt
    When der TDD-Loop den Ablauf erzwingt
    Then wird die Testdatei zuerst auf Disk geschrieben
    And erst danach wird die Implementierungsdatei geschrieben

  Scenario: pytest schlägt fehl (fail-Ergebnis)
    Given das lokale LLM schreibt einen Test
    And die Implementierung besteht den Test nicht (pytest exit-code != 0)
    When der TDD-Loop für TSK-001 ausgeführt wird
    Then enthält das Loop-Ergebnis status "fail"
    And enthält pytest-stdout den Fehler-Output
    And enthält das Ergebnis iteration 1

  Scenario: Concurrent Tasks werden begrenzt (Semaphore)
    Given task_routing.max_concurrent ist 2
    And 5 Tasks mit executor "local" stehen gleichzeitig an
    When asyncio.gather die Tasks startet
    Then laufen zu keinem Zeitpunkt mehr als 2 Tasks gleichzeitig
    And alle 5 Tasks werden schließlich abgeschlossen

  Scenario: LLM-Aufruf via SPEC-0008 Factory
    Given llm.local_llm.provider ist openai-compat
    When der LocalLLMExecutor einen Prompt sendet
    Then nutzt er get_completion_provider(config, "local_llm")
    And kein direkter openai.OpenAI()-Aufruf findet im Executor statt

  Scenario: Async pytest-Aufruf blockiert Event-Loop nicht
    Given 3 Tasks laufen gleichzeitig
    When pytest für Task 1 ausgeführt wird (dauert 2s)
    Then können Task 2 und Task 3 gleichzeitig LLM-Calls absetzen
    And der Event-Loop ist nicht blockiert

  Scenario: LLM-Timeout während Test-Generierung
    Given das lokale LLM antwortet nicht innerhalb des konfigurierten Timeouts
    When der LocalLLMExecutor auf die Completion wartet
    Then wird eine TimeoutError-Exception geworfen
    And das Loop-Ergebnis enthält status "fail" mit Begründung "LLM timeout"
    And keine Testdatei wird auf Disk geschrieben
```
