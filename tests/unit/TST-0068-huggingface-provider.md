---
id: TST-0068
project: PRJ-0001
title: "HuggingFace Provider + Factory Unit-Tests"
level: unit
spec: SPEC-0013
contract: CON-0031
status: implemented
framework: pytest
artifact: "tests/unit/test_huggingface_provider.py"
version: "0.1.0"
tags: ["llm", "huggingface", "inference-api", "mock", "factory"]
---

# Test: HuggingFace Provider + Factory Unit-Tests

> **Spec:** SPEC-0013 · **Level:** Unit · **Contracts:** CON-0031, CON-0032, CON-0033

## Zweck

Prüft `HuggingFaceCompletionProvider` (alle drei Modi) und die Factory-Integration
via `sys.modules`-Mock ohne echten HF-API-Aufruf.

## Test Cases

### Serverless-Modus (CON-0031 G-02)

| TC    | Was wird geprüft?                                                                          |
|-------|--------------------------------------------------------------------------------------------|
| TC-01 | `complete()` sendet `model` und `max_new_tokens` an `text_generation()`                   |
| TC-02 | `complete()` gibt `CompletionResult` mit `usage.estimated=True` zurück                    |
| TC-03 | `usage.input_tokens` und `output_tokens` per Wörter-Schätzung befüllt                    |
| TC-04 | `system_prompt` als `<system>...</system>\\n\\n` vorangestellt                             |
| TC-05 | `temperature=0` → kein `do_sample`/`temperature` im Request (greedy)                     |
| TC-06 | `temperature>0` → `do_sample=True` und `temperature` gesetzt                             |
| TC-07 | HTTP 503 → `RuntimeError` mit "503" in der Meldung                                        |
| TC-08 | Antwort ohne `generated_text` → `ValueError`                                              |
| TC-09 | `InferenceClient` wird nur einmal im Konstruktor erzeugt (nicht pro Aufruf)              |
| TC-10 | Fehlendes `huggingface_hub` → `RuntimeError("pip install 'sdd-cli[huggingface]'")`       |

### Dedicated-Modus (CON-0031 G-03)

| TC    | Was wird geprüft?                                                              |
|-------|--------------------------------------------------------------------------------|
| TC-11 | `InferenceClient` wird mit `base_url=endpoint_url` initialisiert              |
| TC-12 | Kein `model`-Parameter in `text_generation()` (Endpoint impliziert Modell)    |

### Local-Modus (CON-0031 G-04/G-05)

| TC    | Was wird geprüft?                                                              |
|-------|--------------------------------------------------------------------------------|
| TC-13 | `transformers.pipeline("text-generation", model=...)` wird genutzt            |
| TC-14 | Pipeline wird gecacht (zweiter Aufruf lädt nicht neu)                         |
| TC-15 | Kein `chat_template` → XML-Präfix für `system_prompt`                        |
| TC-16 | `chat_template` vorhanden → `apply_chat_template()` mit korrekten kwargs      |
| TC-17 | `usage.estimated=True` im local-Modus                                         |
| TC-18 | Fehlendes `transformers` → `RuntimeError("pip install 'sdd-cli[huggingface-local]'")` |
| TC-19 | `OSError` beim Laden (kein Cache) → `RuntimeError` mit Cache-Hinweis         |

### Factory-Integration (CON-0032, CON-0033)

| TC    | Was wird geprüft?                                                              |
|-------|--------------------------------------------------------------------------------|
| TC-20 | `provider: huggingface` → `HuggingFaceCompletionProvider` mit `hf_token`     |
| TC-21 | `hf_mode: dedicated` + `endpoint_url` → Provider korrekt initialisiert       |
| TC-22 | `dedicated` ohne `endpoint_url` → `ValueError`                               |
| TC-23 | `hf_token: "${MY_HF_TOKEN}"` + Variable fehlt → `RuntimeError` mit Var-Name  |
| TC-24 | `code_gen.provider: huggingface` → `ValueError`                              |
| TC-25 | Bestehende `anthropic`-Branch unverändert (OCP-Verifikation)                 |
| TC-26 | `serverless` ohne `hf_token` → `RuntimeError`                               |

## Ausführung

```bash
pytest tests/unit/test_huggingface_provider.py -v
```
