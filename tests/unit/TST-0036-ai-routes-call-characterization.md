---
id: TST-0036
project: PRJ-0001
title: "Charakterisierungstest: routes/ai._call"
level: unit
spec: SPEC-0008
contract: CON-0022
status: implemented
framework: pytest
artifact: "tests/unit/test_llm_characterization.py"
version: "0.1.0"
tags: ["llm", "ai-routes", "usage-store", "characterization", "regression", "fr-17"]
---

# Test: Charakterisierungstest – routes/ai._call

> **Spec:** SPEC-0008 · **Level:** Unit · **Contract:** CON-0022 · **FR-17**

## Zweck

Sichert den Vertrag von `ai._call(operation, user_message) → (str, dict)`:
Usage-Tracking via `usage_store`, No-Op bei `usage=None`, `RuntimeError`→503,
`system_prompt`-Weiterleitung. Merge-Blocker gemäß FR-17.

## Test Cases

| TC    | Was wird geprüft?                                                                 |
|-------|-----------------------------------------------------------------------------------|
| TC-01 | Gibt `(text: str, entry: dict)` Tuple zurück                                     |
| TC-02 | `usage_store.record_usage()` wird aufgerufen wenn `result.usage` nicht `None`    |
| TC-03 | `usage_store.record_usage()` wird NICHT aufgerufen wenn `result.usage` `None`    |
| TC-04 | `RuntimeError` vom Provider → `HTTPException 503`                                |
| TC-05 | `SDD_SYSTEM_PROMPT` wird als `system_prompt` an `provider.complete()` übergeben  |

## Ausführung

```bash
pytest tests/unit/test_llm_characterization.py::TestAiRoutesCall -v
```
