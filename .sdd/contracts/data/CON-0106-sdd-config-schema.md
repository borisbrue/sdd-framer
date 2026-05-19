---
id: CON-0106
title: "SDD Config Schema – llm_pool und docker in config.yaml"
type: data
format: json-schema
spec: SPEC-0027
version: 0.1.0
status: draft
artifact: "contracts/data/sdd-config.schema.json"
tests:
- TST-0125
---

# Contract: SDD Config Schema – llm_pool und docker in config.yaml

> **Spec:** SPEC-0027 · **Typ:** Daten (JSON Schema) · **Status:** draft

## Zweck

Definiert die Schema-Struktur der Abschnitte `llm_pool` und `docker` in `.sdd/config.yaml`.
Dieses Schema ist maßgeblich für Wizard, `sdd config validate` und CI/CD-Setups.
API-Keys dürfen niemals direkt im Schema erscheinen — nur Env-Var-Namen (FR-05, FR-07, FR-13–16).

## Invarianten

- **INV-01:** `llm_pool.providers` ist eine nicht-leere Liste; jede Provider-ID ist eindeutig.
- **INV-02:** Remote-Provider (`type: remote`) müssen `api_key_env` setzen; local-Provider brauchen es nicht.
- **INV-03:** `llm_pool.strategy` ist einer von: `cost_first`, `quality_first`, `local_first`.
- **INV-04:** `docker.max_parallel_containers` ≥ 1 (positiver Integer).
- **INV-05:** `docker.resources.cpu_limit` ist ein String im Format eines positiven Float (z.B. "1.0").
- **INV-06:** `docker.resources.memory_limit` ist ein String in Docker-Notation (z.B. "1g", "512m", "2048m").
- **INV-07:** Wenn `docker.registry.url` gesetzt ist, muss `docker.registry.auth_env` gesetzt sein.

## Beispiele

**Gültig:**
```yaml
llm_pool:
  strategy: local_first
  providers:
    - id: ollama-mistral
      type: local
      model: mistral:7b
      cost_tier: cheap
      max_context_tokens: 32000
      base_url: http://localhost:11434
    - id: claude-sonnet
      type: remote
      model: claude-sonnet-4-6
      cost_tier: standard
      max_context_tokens: 200000
      api_key_env: ANTHROPIC_API_KEY

docker:
  runtime: docker
  image: sdd-dev:latest
  dockerfile: .sdd/Dockerfile
  max_parallel_containers: 2
  resources:
    cpu_limit: "1.0"
    memory_limit: "1g"
  cleanup:
    on_success: true
    on_failure: false
  registry:
    url: ''
    auth_env: ''
  skip_if_unavailable: false
```

**Ungültig (und warum):**
```yaml
llm_pool:
  providers:
    - id: claude-sonnet
      type: remote
      model: claude-sonnet-4-6
      api_key_env: sk-ant-abc123   # Direkter Key! Verstößt gegen INV-02
docker:
  max_parallel_containers: 0       # < 1, verstößt gegen INV-04
```
→ Verstößt gegen INV-02 (api_key_env muss Env-Var-Name sein, kein Klartext)
→ Verstößt gegen INV-04 (max_parallel_containers muss ≥ 1 sein)

## Validierung

- Schema unter `contracts/data/sdd-config.schema.json` (JSON Schema Draft 2020-12)
- Python-Validierung via `jsonschema` in `config_manager.py`
- Wird von `sdd config validate` und Wizard nach jeder Section-Eingabe aufgerufen
