---
id: TST-0034
project: PRJ-0001
title: "Charakterisierungstest: orchestrator._call_code_gen_agent"
level: unit
spec: SPEC-0008
contract: CON-0024
status: implemented
framework: pytest
artifact: "tests/unit/test_llm_characterization.py"
version: "0.1.0"
tags: ["llm", "orchestrator", "code-gen", "characterization", "regression", "fr-17"]
---

# Test: Charakterisierungstest – orchestrator._call_code_gen_agent

> **Spec:** SPEC-0008 · **Level:** Unit · **Contract:** CON-0024 · **FR-17**

## Zweck

Sichert den Vertrag von `_call_code_gen_agent(...) → (list[dict], str)` nach dem
Provider-Refactor: Delegation an Provider, Prompt-Inhalt, Timeout-Weiterleitung,
Workspace-Binding. Merge-Blocker gemäß FR-17.

## Test Cases

| TC    | Was wird geprüft?                                                            |
|-------|------------------------------------------------------------------------------|
| TC-01 | Gibt `(list[dict], str)` Tuple zurück                                        |
| TC-02 | `timeout`-Parameter wird an `provider.generate()` weitergereicht            |
| TC-03 | `spec_id` erscheint im Prompt                                                |
| TC-04 | `error_context` erscheint im Prompt bei Retry                                |
| TC-05 | `workspace`-Argument an Provider ist `config.root`                           |

## Ausführung

```bash
pytest tests/unit/test_llm_characterization.py::TestOrchestratorCallCodeGenAgent -v
```
