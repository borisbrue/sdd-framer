---
id: TST-0197
project: PRJ-0001
title: "Task-Routing-Entscheidung – complexity_score → executor"
level: unit
spec: SPEC-0045
contract: CON-0171
status: draft
framework: pytest
artifact: "tests/unit/test_tst_0197.py"
tags:
  - task-routing
  - complexity-score
  - local-llm
---

# Test: Task-Routing-Entscheidung

> **Level:** unit · **Spec:** SPEC-0045 · **Contract:** CON-0171

## Was wird geprüft?

Prüft die Routing-Logik: `complexity_score` und Konfiguration bestimmen ob ein Task
`executor: local` oder `executor: claude` erhält.

## Vorbedingungen

- `tool/sdd_cli/task_routing/router.py` mit `decide_executor(task, config)` existiert
- `TaskRoutingConfig` Dataclass mit `enabled`, `complexity_threshold`, `max_retries`,
  `max_concurrent` existiert

## Ablauf

1. TaskRoutingConfig mit verschiedenen Werten instanziieren
2. `decide_executor()` mit Task + Config aufrufen
3. Rückgabewert `"local"` oder `"claude"` prüfen

## Verknüpfung mit Contract (CON-0171)

- [x] INV-01: complexity_score ist integer 0–100
- [x] INV-02: executor ist immer gesetzt
- [x] INV-03: disabled/kein llm.local_llm → immer claude
- [x] INV-04: Schwellenwert-Vergleich ≤ (inklusiv)
- [x] INV-05: Deterministisch
