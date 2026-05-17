---
id: CON-0032
project: PRJ-0001
title: "Konfigurationsschema für provider: huggingface"
type: data
format: markdown
spec: SPEC-0013
version: 0.1.0
status: active
artifact: ".sdd/config.yaml"
tests: ["TST-0068"]
---

# Contract: Konfigurationsschema für provider: huggingface

> **Spec:** SPEC-0013 · **Typ:** Daten · **Status:** implemented

## Zweck

Spezifiziert die Felder der `huggingface`-Provider-Sektion in `.sdd/config.yaml`.
Ergänzt CON-0023 (llm-Konfigurationsschema allgemein) um HF-spezifische Felder.

## Schema

```yaml
llm:
  completion:
    provider: huggingface

    # Pflicht für serverless und local; optional für dedicated
    model: "mistralai/Mistral-7B-Instruct-v0.3"

    # Pflicht für serverless und dedicated; optional für local
    # Unterstützt ${ENV_VAR}-Syntax (z.B. "${HF_TOKEN}")
    hf_token: "${HF_TOKEN}"

    # serverless | dedicated | local; Default: serverless
    hf_mode: serverless

    # Pflicht für hf_mode: dedicated
    # endpoint_url: "https://xyz.endpoints.huggingface.cloud"

    # Optional; Default: 0.0
    temperature: 0.0
```

## Feldspezifikation

| Feld           | Typ    | Pflicht                              | Default        | Beschreibung                                        |
|----------------|--------|--------------------------------------|----------------|-----------------------------------------------------|
| `provider`     | string | Ja                                   | –              | Muss `"huggingface"` sein                           |
| `model`        | string | serverless + local: Pflicht          | –              | HF-Modell-ID (z.B. `"mistralai/Mistral-7B-Instruct-v0.3"`) |
| `hf_token`     | string | serverless + dedicated: Pflicht      | –              | HF API-Token; unterstützt `${ENV_VAR}`-Syntax       |
| `hf_mode`      | string | Nein                                 | `"serverless"` | `serverless` \| `dedicated` \| `local`              |
| `endpoint_url` | string | dedicated: Pflicht                   | –              | URL des Dedicated Endpoint                          |
| `temperature`  | float  | Nein                                 | `0.0`          | Sampling-Temperatur; 0.0 = greedy decoding          |

## Pflichtfelder je Modus

| Modus        | Pflichtfelder                     | Optionale Felder      |
|--------------|-----------------------------------|-----------------------|
| `serverless` | `model`, `hf_token`               | `temperature`         |
| `dedicated`  | `endpoint_url`, `hf_token`        | `model`, `temperature`|
| `local`      | `model`                           | `hf_token`, `temperature` |

## Garantien

### G-01: ENV-VAR-Auflösung

`hf_token: "${MY_VAR}"` wird zur Laufzeit via `os.environ.get("MY_VAR")` aufgelöst.
Ist die Variable nicht gesetzt → `RuntimeError` mit Nennung des Variablennamens.

### G-02: Validierung zur Laufzeit

Pflichtfeld-Prüfungen erfolgen in `get_completion_provider()`, nicht in `load_config()`.

### G-03: Fehlende Pflichtfelder

| Fehlerfall                                        | Exception                           |
|---------------------------------------------------|-------------------------------------|
| `dedicated` ohne `endpoint_url`                  | `ValueError` mit "endpoint_url"     |
| `serverless`/`dedicated` ohne `hf_token`         | `RuntimeError` mit "hf_token"       |
| `serverless`/`local` ohne `model`               | `ValueError` mit "model"            |
| `hf_token` referenziert nicht gesetzte Env-Var  | `RuntimeError` mit Var-Name         |

### G-04: Sicherheit

`hf_token` erscheint niemals in Logs, Rich-Output, Report-JSON oder
Subprocess-Argumenten — analog zur `api_key`-Behandlung in CON-0022 G-06.

## Beispielkonfigurationen

### Serverless (Standard)

```yaml
llm:
  completion:
    provider: huggingface
    model: "mistralai/Mistral-7B-Instruct-v0.3"
    hf_token: "${HF_TOKEN}"
```

### Dedicated Endpoint

```yaml
llm:
  completion:
    provider: huggingface
    hf_mode: dedicated
    endpoint_url: "https://xyz.endpoints.huggingface.cloud"
    hf_token: "${HF_TOKEN}"
```

### Lokale Ausführung (kein API-Key)

```yaml
llm:
  completion:
    provider: huggingface
    hf_mode: local
    model: "gpt2"
```

### Gemischt: HF für Evaluator, Claude CLI für Code-Gen

```yaml
llm:
  completion:
    provider: huggingface
    model: "mistralai/Mistral-7B-Instruct-v0.3"
    hf_token: "${HF_TOKEN}"
  code_gen:
    provider: claude-cli
  evaluator:
    hf_mode: serverless
```
