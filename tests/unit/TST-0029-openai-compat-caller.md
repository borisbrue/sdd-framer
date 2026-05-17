---
id: TST-0029
project: PRJ-0001
title: "OpenAICompatCompletionProvider Unit-Tests"
level: unit
spec: SPEC-0008
contract: CON-0022
status: planned
framework: pytest
artifact: "tests/unit/test_llm_providers.py"
tags: ["llm", "openai-compat", "completion", "mock", "lm-studio"]
---

# Test: OpenAICompatCompletionProvider Unit-Tests

> **Spec:** SPEC-0008 · **Level:** Unit · **Contract:** CON-0022

## Zweck

Prüft `OpenAICompatCompletionProvider.complete()` via `unittest.mock.patch`:
korrektes Client-Setup, API-Aufruf-Parameter, Response-Parsing und
Fehlerbehandlung — kein echter HTTP-Request, kein laufendes LM Studio nötig.

## Test Cases

| TC    | Was wird geprüft?                                                                     |
|-------|---------------------------------------------------------------------------------------|
| TC-01 | `openai.OpenAI(base_url=..., api_key=...)` erhält konfigurierte Werte                 |
| TC-02 | `chat.completions.create()` wird mit `model`, `messages=[{"role":"user",...}]`, `max_tokens=512`, `temperature=0` aufgerufen |
| TC-03 | Valide Text-Antwort wird unverändert als `str` zurückgegeben                          |
| TC-04 | `api_key`-Default `"lm-studio"` bei fehlendem Konfigurationsfeld                      |
| TC-05 | `api_key` erscheint nicht im Rückgabewert von `complete()`                            |
| TC-06 | `max_tokens`-Parameter wird an `chat.completions.create()` weitergereicht             |
| TC-07 | Fehlendes `openai`-Paket → `RuntimeError` mit `"lm-studio"` im Text                  |
| TC-08 | `openai.APIConnectionError` wird als Exception propagiert (kein stilles Schlucken)    |
| TC-09 | `isinstance(provider, CompletionProvider)` → `True`                                   |

## Ausführung

```bash
pytest tests/unit/test_openai_compat_completion.py -v
```
