---
id: CON-0022
project: PRJ-0001
title: "CompletionProvider-Interface und Implementierungen"
type: behavior
format: markdown
spec: SPEC-0008
version: 0.3.0
status: draft
artifact: "tool/sdd_cli/llm/"
tests: ["TST-0028", "TST-0029"]
---

# Contract: CompletionProvider-Interface und Implementierungen

> **Spec:** SPEC-0008 · **Typ:** Verhalten · **Status:** draft

## Zweck

Spezifiziert das `CompletionProvider`-Protocol und alle Implementierungen, die
es erfüllen. Dieser Contract gilt für die Komponenten **Evaluator**, **Analyzer**
und **AI-Routes**.

## Protokoll-Definition

```python
@runtime_checkable
class CompletionProvider(Protocol):
    def complete(self, prompt: str, *, max_tokens: int = 512) -> str: ...
```

- `prompt`: Plain-Text-Eingabe, beliebige Länge
- `max_tokens`: Hint an das Modell; Implementierungen dürfen einen eigenen Mindestwert durchsetzen
- Rückgabe: **roher Text** — JSON-Parsing liegt beim Aufrufer
- Bei Fehler: wirft Exception (kein `None`-Rückgabe, kein leerer String bei Fehler)

## Garantien

### G-01: AnthropicCompletionProvider

- Lazy-importiert `anthropic`; fehlt das Paket → `RuntimeError("... pip install 'sdd-cli[evaluate]'")`
- Liest `ANTHROPIC_API_KEY` aus der Umgebung; fehlt er → `RuntimeError`
- Nutzt `client.messages.create(model=..., max_tokens=..., messages=[{"role":"user","content":prompt}])`
- Rückgabe: `response.content[0].text`

### G-02: ClaudeCliCompletionProvider

- Sucht `claude` via `shutil.which`; fehlt es → `RuntimeError("claude CLI nicht gefunden")`
- Ruft `claude --print --output-format json` ohne Tools, Einstellungen, MCP und Auto-Memory auf;
  Prompt über stdin, System-Prompt per `--system-prompt` (Aufrufform: CON-0233)
- Strippt den äußeren JSON-Envelope `{"type":"result","result":"<text>",...}` und gibt `result` zurück
- Timeout via `subprocess.run(..., timeout=<max_tokens_based_or_120>)`
- Rückgabe: innerer Text (noch vor JSON-Parsing durch den Aufrufer)

### G-03: OpenAICompatCompletionProvider

- Lazy-importiert `openai`; fehlt das Paket → `RuntimeError("... pip install 'sdd-cli[lm-studio]'")`
- Instantiiert `openai.OpenAI(base_url=base_url, api_key=api_key)`
- Ruft `client.chat.completions.create(model=model, messages=[{"role":"user","content":prompt}], max_tokens=max_tokens, temperature=0)` auf
- Rückgabe: `response.choices[0].message.content.strip()`

### G-04: Factory-Auflösung

`get_completion_provider(config, component)` löst in dieser Reihenfolge auf:

```
config.raw["llm"][component]           (z.B. "evaluator", "analyzer", "ai_routes")
  ↓ fehlt?
config.raw["llm"]["completion"]        (globaler Completion-Default)
  ↓ fehlt?
Built-in-Default: AnthropicCompletionProvider + claude-haiku-4-5-20251001
```

### G-05: Erlaubte Provider-Werte (CompletionProvider)

`anthropic`, `claude-cli`, `openai-compat`. Jeder andere Wert → `ValueError` mit
Liste der erlaubten Werte.

### G-06: api_key-Behandlung

`api_key` wird niemals in Logs, Rich-Output, Report-JSON oder als
Subprocess-Argument übergeben. Bei `openai-compat`: Default `"lm-studio"` wenn
nicht gesetzt oder leer.

## Invarianten

- **INV-01:** Kein `anthropic`-, `openai`- oder `subprocess`-Import auf Modul-Ebene; ausschließlich lazy imports innerhalb von Provider-Konstruktoren.
- **INV-02:** `complete()` ist stateless — derselbe Provider kann mehrfach mit verschiedenen Prompts aufgerufen werden.
- **INV-03:** `complete()` gibt niemals `None` zurück; bei Fehler wird immer eine Exception geworfen.
- **INV-04:** Alle Provider-Klassen sind durch `isinstance(provider, CompletionProvider)` prüfbar (`@runtime_checkable`).

## Begriffe

| Begriff                    | Definition                                                       |
|----------------------------|------------------------------------------------------------------|
| `CompletionProvider`       | `typing.Protocol` für synchrones Prompt → Text                  |
| lazy import                | Import erst im Konstruktor oder bei erstem Aufruf                |
| JSON-Envelope              | Der äußere `{"type":"result","result":"..."}` Wrapper der Claude CLI |
| Built-in-Default           | Wird genutzt wenn `llm`-Sektion in config.yaml fehlt            |
