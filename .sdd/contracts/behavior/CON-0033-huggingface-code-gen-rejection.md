---
id: CON-0033
project: PRJ-0001
title: "Factory – huggingface als code_gen-Provider wird abgelehnt"
type: behavior
format: markdown
spec: SPEC-0013
version: 0.1.0
status: deprecated
artifact: "tool/sdd_cli/llm/factory.py"
tests: ["TST-0068"]
deprecated_reason: "CodeGen-Pfad entfernt, damit entfällt die huggingface-Prüfung für code_gen (SPEC-0062)"
---

# Contract: Factory – huggingface als code_gen-Provider wird abgelehnt

> **Spec:** SPEC-0013 · **Typ:** Verhalten · **Status:** implemented

## Zweck

Garantiert, dass `provider: huggingface` ausschließlich als `CompletionProvider`
verfügbar ist. Eine Konfiguration als `code_gen`-Provider wird von der Factory
mit einer erklärenden `ValueError` abgelehnt (FR-06 aus SPEC-0013).

## Garantien

### G-01: Explizite Ablehnung

```python
get_code_gen_provider(config)
```

wirft `ValueError` wenn `llm.code_gen.provider` (oder `llm.orchestrator.provider`)
auf `"huggingface"` gesetzt ist. Die Fehlermeldung enthält `"huggingface"` und
einen Hinweis auf erlaubte Alternativen (`claude-cli`, `openai-compat`).

### G-02: OCP-Konformität

Die Ablehnung ist als expliziter Zweig **vor** der generischen
`_CODE_GEN_PROVIDERS`-Prüfung implementiert. Bestehende `claude-cli`- und
`openai-compat`-Zweige bleiben unverändert.

### G-03: Completion-Pfad unberührt

`get_completion_provider(config)` mit `provider: huggingface` ist weiterhin
gültig und gibt `HuggingFaceCompletionProvider` zurück (CON-0031).

## Begründung

HF-Modelle ohne Funktionsaufruf-Unterstützung eignen sich nicht für agentische
Code-Generierung (Datei-Schreibung in einen Workspace). Der `CodeGenProvider`
erfordert strukturierte Tool-Calls oder ein JSON-Schema-konformes Ausgabeformat,
das HF Instruct-Modelle nicht zuverlässig liefern.
