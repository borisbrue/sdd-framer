---
id: TST-0199
project: PRJ-0001
title: "Claude Review-Gate, Retry-Loop und Eskalation"
level: unit
spec: SPEC-0045
contract: CON-0173
status: draft
framework: pytest
artifact: "tests/unit/test_tst_0199.py"
tags:
  - task-routing
  - review-gate
  - retry
  - escalation
  - claude
---

# Test: Claude Review-Gate, Retry und Eskalation

> **Level:** unit · **Spec:** SPEC-0045 · **Contract:** CON-0173

## Was wird geprüft?

Prüft das Verhalten des Review-Gates: Claude wird nur bei pytest-pass aufgerufen,
Retry akkumuliert Kontext, nach max_retries wird eskaliert.

## Vorbedingungen

- `tool/sdd_cli/task_routing/loop_controller.py` mit `LoopController` existiert
- `LoopController.run(task, config)` ist eine async-Coroutine
- `ClaudeReviewer` und `ClaudeExecutor` sind über SPEC-0008-Provider mockbar

## Ablauf

1. `LoopController` mit gemockten Reviewer/Executor instanziieren
2. Verschiedene pass/fail-Kombinationen durchspielen
3. Task-Status, executor-Feld und Retry-Kontext-Akkumulation prüfen

## Verknüpfung mit Contract (CON-0173)

- [x] INV-01: kein completed ohne Claude-Review; pytest-fail → kein Claude-Aufruf
- [x] INV-02: Claude-Bewertung immer binär mit Begründung bei fail
- [x] INV-03: Retry-Kontext akkumulativ über alle Iterationen
- [x] INV-04: Nach max_retries → Eskalation (nie stilles Verwerfen)
- [x] INV-05: Eskalierter Task via get_code_gen_provider() neu implementiert
- [x] INV-06: Prompt Caching — gecachtes Prefix einmalig pro Lauf
