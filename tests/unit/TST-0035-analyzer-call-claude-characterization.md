---
id: TST-0035
project: PRJ-0001
title: "Charakterisierungstest: analyzer._call_claude"
level: unit
spec: SPEC-0008
contract: CON-0022
status: implemented
framework: pytest
artifact: "tests/unit/test_llm_characterization.py"
version: "0.1.0"
tags: ["llm", "analyzer", "characterization", "regression", "fr-17", "http-exception"]
---

# Test: Charakterisierungstest – analyzer._call_claude

> **Spec:** SPEC-0008 · **Level:** Unit · **Contract:** CON-0022 · **FR-17**

## Zweck

Sichert den Vertrag von `analyzer._call_claude(prompt, provider) → (dict, dict)`:
JSON-Parsing mit Fence-Stripping, Usage-Dict-Aufbau, Fehler→HTTPException-Mapping.
Merge-Blocker gemäß FR-17.

## Test Cases

| TC    | Was wird geprüft?                                                         |
|-------|---------------------------------------------------------------------------|
| TC-01 | Gibt `(geparsten dict, usage dict)` zurück                               |
| TC-02 | JSON in markdown-Fence wird korrekt geparst                              |
| TC-03 | `usage`-Dict enthält mindestens `provider`-Schlüssel                    |
| TC-04 | Token-Counts aus Anthropic-Provider in `usage` abgebildet               |
| TC-05 | `RuntimeError` vom Provider → `HTTPException` (5xx)                     |
| TC-06 | Ungültiges JSON → `HTTPException 502`                                    |

## Ausführung

```bash
pytest tests/unit/test_llm_characterization.py::TestAnalyzerCallClaude -v
```
