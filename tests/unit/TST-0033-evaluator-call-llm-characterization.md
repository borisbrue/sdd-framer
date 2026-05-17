---
id: TST-0033
project: PRJ-0001
title: "Charakterisierungstest: evaluator._call_llm"
level: unit
spec: SPEC-0008
contract: CON-0022
status: implemented
framework: pytest
artifact: "tests/unit/test_llm_characterization.py"
version: "0.1.0"
tags: ["llm", "evaluator", "characterization", "regression", "fr-17"]
---

# Test: Charakterisierungstest – evaluator._call_llm

> **Spec:** SPEC-0008 · **Level:** Unit · **Contract:** CON-0022 · **FR-17**

## Zweck

Sichert den Input→Output-Vertrag von `evaluator._call_llm(provider, prompt) → dict`
nach dem Provider-Refactor. Merge-Blocker gemäß FR-17.

## Test Cases

| TC    | Was wird geprüft?                                             |
|-------|---------------------------------------------------------------|
| TC-01 | Gibt geparsten `dict` aus `provider.complete().text` zurück  |
| TC-02 | JSON wird robust aus umgebendem Text extrahiert               |
| TC-03 | Ungültiges JSON → `JSONDecodeError` oder `ValueError`        |
| TC-04 | Plan-Antwort enthält Schlüssel `method` und `path`           |
| TC-05 | Eval-Antwort enthält Schlüssel `passed` und `reasoning`      |

## Ausführung

```bash
pytest tests/unit/test_llm_characterization.py::TestEvaluatorCallLlm -v
```
