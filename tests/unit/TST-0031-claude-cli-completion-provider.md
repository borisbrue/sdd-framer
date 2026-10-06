---
id: TST-0031
project: PRJ-0001
title: "ClaudeCliCompletionProvider Unit-Tests"
level: unit
spec: SPEC-0008
contract: CON-0022
status: implemented
framework: pytest
artifact: "tests/unit/test_llm_providers.py"
version: "0.1.0"
tags: ["llm", "claude-cli", "completion", "subprocess", "mock"]
---

# Test: ClaudeCliCompletionProvider Unit-Tests

> **Spec:** SPEC-0008 · **Level:** Unit · **Contract:** CON-0022

## Zweck

Prüft `ClaudeCliCompletionProvider.complete()` via `unittest.mock.patch`:
JSON-Envelope-Stripping, Übergabe von system_prompt und Prompt, Timeout-Weiterleitung und
Fehlerbehandlung — kein echter `claude`-Prozess wird gestartet.

## Test Cases

| TC    | Was wird geprüft?                                                                     |
|-------|---------------------------------------------------------------------------------------|
| TC-01 | JSON-Envelope `{"type":"result","result":"..."}` → innerer Text wird zurückgegeben    |
| TC-02 | `system_prompt` geht per `--system-prompt`, der Prompt über stdin (CON-0233)        |
| TC-03 | `timeout`-Parameter wird an `subprocess.run()` weitergereicht                         |
| TC-04 | Envelope ohne Usage-Block → `usage.source == "unavailable"` (SPEC-0060)              |
| TC-05 | `claude` nicht im PATH → `RuntimeError`                                              |
| TC-06 | Kein `system_prompt` → Prompt unverändert über stdin                                 |

## Ausführung

```bash
pytest tests/unit/test_llm_providers.py::TestClaudeCliCompletionProvider -v
```
