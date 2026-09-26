---
id: CON-0174
project: PRJ-0001
title: "task_routing Konfigurationsschema"
type: data
format: json-schema
spec: SPEC-0045
version: 0.1.0
status: deprecated
artifact: ""
tests: ["TST-0200"]
deprecated_reason: "mit SPEC-0045 abgelöst: Task-Routing durch Rollen-Profile und by_complexity der Pipeline abgelöst (SPEC-0062)"
---

# Contract: task_routing Konfigurationsschema

> **Spec:** SPEC-0045 · **Typ:** Data · **Status:** draft

## Zweck

Definiert das Schema des `task_routing`-Blocks in `.sdd/config.yaml` sowie
das `llm.local_llm`-Komponenten-Override (SPEC-0008 Factory-Hierarchie).

## Schema: task_routing

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "TaskRoutingConfig",
  "type": "object",
  "required": [],
  "additionalProperties": false,
  "properties": {
    "enabled": {
      "type": "boolean",
      "default": false,
      "description": "Aktiviert das lokale LLM-Routing. false = alle Tasks zu Claude."
    },
    "complexity_threshold": {
      "type": "integer",
      "minimum": 0,
      "maximum": 100,
      "default": 30,
      "description": "Tasks mit complexity_score <= threshold → executor: local."
    },
    "max_retries": {
      "type": "integer",
      "minimum": 1,
      "maximum": 10,
      "default": 3,
      "description": "Maximale Anzahl lokaler Versuche vor Eskalation zu Claude."
    },
    "max_concurrent": {
      "type": "integer",
      "minimum": 1,
      "maximum": 10,
      "default": 3,
      "description": "Maximale Anzahl gleichzeitig laufender async Tasks (Semaphore)."
    }
  }
}
```

## Schema: llm.local_llm (SPEC-0008 Komponenten-Override)

Der `llm.local_llm`-Block folgt dem Standard-Schema für `openai-compat`-Provider
aus SPEC-0008 (CON-0023). Pflichtfelder wenn `task_routing.enabled: true`:

```yaml
llm:
  local_llm:
    provider: openai-compat   # Pflicht; einziger unterstützter Wert in v0.1.0
    base_url: string          # Pflicht; z.B. "http://localhost:11434/v1"
    model: string             # Pflicht; z.B. "qwen2.5-coder:14b"
    api_key: string           # Optional; Default "lm-studio"; oder "${ENV_VAR}"
    temperature: number       # Optional; Default 0.0
```

## Invarianten

- **INV-01:** Ist `task_routing.enabled: true` und `llm.local_llm` fehlt in der Config,
  verhält sich das System wie `enabled: false` — kein Fehler, alle Tasks zu Claude.
- **INV-02:** Fehlt der gesamte `task_routing`-Block, gelten alle Defaults
  (`enabled: false`, `complexity_threshold: 30`, `max_retries: 3`, `max_concurrent: 3`).
- **INV-03:** `complexity_threshold` muss im Bereich 0–100 liegen; außerhalb → ValueError
  beim Config-Laden.
- **INV-04:** `llm.local_llm.provider` darf in v0.1.0 nur `openai-compat` sein;
  `huggingface` (SPEC-0013) ist als zukünftige Erweiterung vorgesehen.
- **INV-05:** Der `local_llm`-Block wird von der SPEC-0008-Factory aufgelöst —
  `get_completion_provider(config, "local_llm")` erbt fehlende Felder vom
  `llm.completion`-Default (Merge-Semantik aus SPEC-0008 §4.4).

## Beispiel-Konfiguration

```yaml
llm:
  completion:
    provider: anthropic
    model: claude-haiku-4-5-20251001
  local_llm:
    provider: openai-compat
    base_url: "http://localhost:11434/v1"
    model: "qwen2.5-coder:14b"

task_routing:
  enabled: true
  complexity_threshold: 30
  max_retries: 3
  max_concurrent: 3
```
