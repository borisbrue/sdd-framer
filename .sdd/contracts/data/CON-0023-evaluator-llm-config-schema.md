---
id: CON-0023
project: PRJ-0001
title: "llm-Konfigurationsschema (unified provider config)"
type: data
format: markdown
spec: SPEC-0008
version: 0.2.0
status: draft
artifact: ".sdd/config.yaml"
tests: ["TST-0028"]
---

# Contract: llm-Konfigurationsschema

> **Spec:** SPEC-0008 · **Typ:** Daten · **Status:** draft

## Zweck

Spezifiziert das vollständige Schema der neuen optionalen `llm`-Sektion in
`.sdd/config.yaml`. Diese Sektion ersetzt die deprecated Felder
`evaluator.model` und `evaluator.llm.*` (aus SPEC-0008 v0.2.0) und definiert
ein einheitliches Provider-Konfigurationsmodell für alle KI-Komponenten.
Ergänzt CON-0016 (config.yaml-Gesamtschema).

## Vollständiges Schema

```yaml
llm:
  # ── CompletionProvider-Defaults ────────────────────────────────────────────
  # Gilt für: Evaluator, Analyzer, AI-Routes (sofern kein Komponenten-Override)
  completion:
    provider: "anthropic"                    # anthropic | claude-cli | openai-compat
    model: "claude-haiku-4-5-20251001"       # Pflicht für anthropic und openai-compat
    base_url: ~                              # Pflicht für openai-compat
    api_key: ~                               # Optional; Default "lm-studio" für openai-compat

  # ── CodeGenProvider-Defaults ───────────────────────────────────────────────
  # Gilt für: Orchestrator (sofern kein Komponenten-Override)
  code_gen:
    provider: "claude-cli"                   # claude-cli | openai-compat
    model: ~                                 # Pflicht für openai-compat
    base_url: ~                              # Pflicht für openai-compat
    api_key: ~                               # Optional

  # ── Optionale Komponenten-Overrides ────────────────────────────────────────
  # Alle nicht gesetzten Felder werden vom jeweiligen globalen Default geerbt.
  # "evaluator" und "analyzer" erben von "completion".
  # "orchestrator" erbt von "code_gen".
  # "ai_routes" erbt von "completion".
  evaluator:
    provider: ~
    model: ~
    base_url: ~
    api_key: ~

  analyzer:
    provider: ~
    model: ~
    base_url: ~
    api_key: ~

  orchestrator:
    provider: ~
    model: ~
    base_url: ~
    api_key: ~

  ai_routes:
    provider: ~
    model: ~
    base_url: ~
    api_key: ~
```

## Feldspezifikation

### Felder (gelten für alle Blöcke: `completion`, `code_gen`, `evaluator`, `analyzer`, `orchestrator`, `ai_routes`)

| Feld       | Typ    | Pflicht                                      | Default               | Beschreibung                                        |
|------------|--------|----------------------------------------------|-----------------------|-----------------------------------------------------|
| `provider` | string | Wenn Block gesetzt                           | Block-spezifisch (s.u.) | Provider-Identifier                               |
| `model`    | string | Bei `anthropic` und `openai-compat`          | Block-spezifisch (s.u.) | Modell-Name im jeweiligen Backend                 |
| `base_url` | string | Bei `openai-compat`                          | –                     | API-Endpunkt (z.B. `http://localhost:1234/v1`)      |
| `api_key`  | string | Nein                                         | `"lm-studio"`         | API-Key; wird nie geloggt                           |

### Provider-Defaults je Block

| Block         | Default `provider` | Default `model`              |
|---------------|--------------------|------------------------------|
| `completion`  | `anthropic`        | `claude-haiku-4-5-20251001`  |
| `code_gen`    | `claude-cli`       | –                            |
| `evaluator`   | (erbt completion)  | (erbt completion)            |
| `analyzer`    | (erbt completion)  | (erbt completion)            |
| `orchestrator`| (erbt code_gen)    | (erbt code_gen)              |
| `ai_routes`   | (erbt completion)  | (erbt completion)            |

### Erlaubte Provider-Werte

| Verwendet in           | Erlaubte Werte                          |
|------------------------|-----------------------------------------|
| `completion`           | `anthropic`, `claude-cli`, `openai-compat` |
| `code_gen`             | `claude-cli`, `openai-compat`           |
| Komponenten-Overrides  | Je nach Basis-Block (s.o.)              |

## Garantien

### G-01: Vollständige Optionalität

Die gesamte `llm`-Sektion ist optional. Fehlt sie, verhalten sich alle
Komponenten identisch zu v0.1.x.

### G-02: Hierarchische Auflösung

Die Factory löst Felder in genau dieser Reihenfolge auf (erstes nicht-`null` gewinnt):
1. `llm.<component>.<field>`
2. `llm.<default_block>.<field>` (`completion` oder `code_gen`)
3. Built-in-Hardcode-Default

### G-03: Validierung zur Laufzeit

`load_config()` führt **keine** Validierung der `llm`-Sektion durch.
Pflichtfeld-Prüfungen (`base_url`, `model` bei `openai-compat`) erfolgen
bei `get_completion_provider()` / `get_code_gen_provider()`.

### G-04: Deprecated Felder

`evaluator.model` (Felder direkt unter `evaluator`, ohne `llm`-Prefix) bleiben
gültig und werden von der Factory in Stufe 2 der Hierarchie berücksichtigt:

```
Stufe 1: llm.evaluator.model
Stufe 2: llm.completion.model  ODER  evaluator.model  (deprecated)
Stufe 3: "claude-haiku-4-5-20251001"
```

Das Feld `evaluator.llm.*` (SPEC-0008 v0.2.0) wird als Alias für `llm.evaluator.*`
aufgelöst (Stufe 1).

### G-05: api_key-Sicherheit

`api_key` darf weder in `sdd evaluate`-Ausgaben noch in Report-JSON, Logs oder
Subprocess-Argumenten erscheinen.

## Beispielkonfigurationen

### Vollständig lokal (LM Studio für alle Komponenten)

```yaml
llm:
  completion:
    provider: openai-compat
    base_url: "http://localhost:1234/v1"
    model: "lmstudio-community/Meta-Llama-3.1-8B-Instruct-GGUF"
  code_gen:
    provider: openai-compat
    base_url: "http://localhost:1234/v1"
    model: "lmstudio-community/Codestral-22B-v0.1-GGUF"
```

### Gemischt: Evaluator lokal, Orchestrator via Claude CLI

```yaml
llm:
  completion:
    provider: anthropic
    model: claude-haiku-4-5-20251001
  code_gen:
    provider: claude-cli
  evaluator:
    provider: openai-compat
    base_url: "http://localhost:1234/v1"
    model: "lmstudio-community/Meta-Llama-3.1-8B-Instruct-GGUF"
```

### Ollama als Backend

```yaml
llm:
  completion:
    provider: openai-compat
    base_url: "http://localhost:11434/v1"
    model: "llama3.1:8b"
    api_key: "ollama"
```
