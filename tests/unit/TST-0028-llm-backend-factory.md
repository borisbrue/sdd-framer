---
id: TST-0028
project: PRJ-0001
title: "LLM-Provider-Factory Unit-Tests"
level: unit
spec: SPEC-0008
contract: CON-0022
status: planned
framework: pytest
artifact: "tests/unit/test_llm_providers.py"
tags: ["llm", "provider", "factory", "solid", "completion", "code-gen"]
---

# Test: LLM-Provider-Factory Unit-Tests

> **Spec:** SPEC-0008 · **Level:** Unit · **Contracts:** CON-0022, CON-0023, CON-0024

## Zweck

Prüft `get_completion_provider()` und `get_code_gen_provider()`: korrekte
Provider-Auflösung, Config-Hierarchie, Fehlerbehandlung — vollständig ohne
echte LLM-Verbindung.

## Test Cases: CompletionProvider-Factory

| TC    | Config-Zustand                                             | Erwartetes Ergebnis                                              |
|-------|------------------------------------------------------------|------------------------------------------------------------------|
| TC-01 | `llm`-Sektion fehlt komplett                               | `AnthropicCompletionProvider`, Haiku-Default-Modell             |
| TC-02 | `llm.completion.provider: anthropic`                       | `AnthropicCompletionProvider`                                    |
| TC-03 | `llm.completion.provider: claude-cli`                      | `ClaudeCliCompletionProvider`                                    |
| TC-04 | `llm.completion.provider: openai-compat` + alle Pflichtfelder | `OpenAICompatCompletionProvider`                              |
| TC-05 | `llm.completion.provider: openai-compat`, `base_url` fehlt | `ValueError` in Factory                                         |
| TC-06 | `llm.completion.provider: openai-compat`, `model` fehlt    | `ValueError` in Factory                                         |
| TC-07 | `llm.evaluator` Override mit `openai-compat`               | Evaluator-Override wird bevorzugt                               |
| TC-08 | `llm.evaluator.provider` Override, `model` vom completion-Default geerbt | Feld-Vererbung funktioniert                       |
| TC-09 | `evaluator.model` (deprecated) gesetzt                     | Wird als Fallback erkannt; `llm.completion.model` hat Vorrang   |
| TC-10 | `provider: unbekannt`                                      | `ValueError` mit Liste erlaubter Werte                           |
| TC-11 | `get_completion_provider(config, "analyzer")`              | Nutzt `llm.analyzer` → `llm.completion` → Built-in             |
| TC-12 | `get_completion_provider(config, "ai_routes")`             | Nutzt `llm.ai_routes` → `llm.completion` → Built-in            |
| TC-13 | Alle Provider erfüllen `isinstance(p, CompletionProvider)` | `True` für alle drei Implementierungen                          |

## Test Cases: CodeGenProvider-Factory

| TC    | Config-Zustand                                             | Erwartetes Ergebnis                                              |
|-------|------------------------------------------------------------|------------------------------------------------------------------|
| TC-14 | `llm.code_gen` fehlt                                       | `ClaudeCliCodeGenProvider` (Built-in-Default)                    |
| TC-15 | `llm.code_gen.provider: claude-cli`                        | `ClaudeCliCodeGenProvider`                                       |
| TC-16 | `llm.code_gen.provider: openai-compat` + alle Pflichtfelder | `OpenAICompatCodeGenProvider`                                   |
| TC-17 | `llm.orchestrator` Override                                | Orchestrator-Override hat Vorrang vor `code_gen`                |
| TC-18 | `provider: openai-compat`, `openai` nicht installiert      | `RuntimeError` mit `"lm-studio"` im Text                        |
| TC-19 | Alle Provider erfüllen `isinstance(p, CodeGenProvider)`    | `True` für beide Implementierungen                               |

## Ausführung

```bash
pytest tests/unit/test_llm_provider_factory.py -v
```
