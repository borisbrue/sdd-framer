---
id: TST-0032
project: PRJ-0001
title: "AnthropicCompletionProvider Unit-Tests"
level: unit
spec: SPEC-0008
contract: CON-0022
status: implemented
framework: pytest
artifact: "tests/unit/test_llm_providers.py"
version: "0.1.0"
tags: ["llm", "anthropic", "completion", "cache-control", "mock"]
---

# Test: AnthropicCompletionProvider Unit-Tests

> **Spec:** SPEC-0008 · **Level:** Unit · **Contract:** CON-0022

## Zweck

Prüft `AnthropicCompletionProvider.complete()` via `sys.modules`-Mock: korrekte
API-Parameter, `CompletionResult`-Rückgabe mit `UsageMetadata`, `cache_control`
für `system_prompt` und Fehlerbehandlung — kein Anthropic-API-Key benötigt.

## Test Cases

| TC    | Was wird geprüft?                                                                     |
|-------|---------------------------------------------------------------------------------------|
| TC-01 | Valide Antwort → `CompletionResult` mit `text` und `UsageMetadata`                   |
| TC-02 | `system_prompt` → `system`-Parameter mit `cache_control: ephemeral`                  |
| TC-03 | Kein `system_prompt` → kein `system`-Parameter im API-Call                           |
| TC-04 | `timeout`-Parameter wird an SDK weitergereicht                                        |
| TC-05 | Cache-Tokens aus Antwort in `UsageMetadata` abgebildet                               |
| TC-06 | Fehlender API-Key → `RuntimeError`                                                    |
| TC-07 | Fehlendes `anthropic`-Paket → `RuntimeError`                                         |

## Ausführung

```bash
pytest tests/unit/test_llm_providers.py::TestAnthropicCompletionProvider -v
```
