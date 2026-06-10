---
id: TST-0198
project: PRJ-0001
title: "Async TDD-Loop – test → implement → pytest (LocalLLMExecutor)"
level: unit
spec: SPEC-0045
contract: CON-0172
status: draft
framework: pytest
artifact: "tests/unit/test_tst_0198.py"
tags:
  - task-routing
  - local-llm
  - async
  - tdd-loop
---

# Test: Async TDD-Loop

> **Level:** unit · **Spec:** SPEC-0045 · **Contract:** CON-0172

## Was wird geprüft?

Prüft den Pflichtablauf des lokalen TDD-Loops: Testdatei vor Implementierung,
pytest via asyncio, Concurrency-Semaphore, LLM-Timeout-Handling.

## Vorbedingungen

- `tool/sdd_cli/task_routing/local_llm.py` mit `LocalLLMExecutor` existiert
- `LocalLLMExecutor.execute(task, config)` ist eine async-Coroutine
- `get_completion_provider(config, "local_llm")` aus SPEC-0008 ist mockbar

## Ablauf

1. `LocalLLMExecutor` mit gemocktem `CompletionProvider` instanziieren
2. `execute()` als asyncio-Coroutine aufrufen
3. Reihenfolge Testdatei/Implementierung + pytest-Aufruf prüfen

## Verknüpfung mit Contract (CON-0172)

- [x] INV-01: Test vor Implementierung auf Disk
- [x] INV-02: Testdatei unter `tests/unit/test_<task_id>.py`
- [x] INV-03: pytest via asyncio.create_subprocess_exec (kein blocking call)
- [x] INV-04: Loop-Ergebnis enthält pass|fail, stdout, returncode, iteration
- [x] INV-05: Semaphore begrenzt max_concurrent Tasks
- [x] INV-06: LLM-Call via get_completion_provider (kein direkter HTTP-Call)
