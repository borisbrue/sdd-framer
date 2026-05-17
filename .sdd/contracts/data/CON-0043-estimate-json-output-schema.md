---
id: CON-0043
project: PRJ-0001
title: "Schema des estimate --json Outputs"
type: data
format: json-schema
spec: SPEC-0011
version: 0.1.0
status: review
artifact: "contracts/data/estimate-json-output.schema.json"
tests:
- TST-0058
---

# Contract: Schema des `estimate --json` Outputs

> **Spec:** SPEC-0011 · **Typ:** Daten · **Status:** review

## Zweck

Definiert das maschinenlesbare JSON-Format von `sdd estimate SPEC-XXXX --json`.

## Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "SDD Estimate Result",
  "type": "object",
  "required": [
    "spec_id", "estimated_input_tokens", "estimated_output_tokens",
    "estimated_usd", "confidence", "model", "n_data_points",
    "budget_exceeded", "neighbors"
  ],
  "properties": {
    "spec_id": {
      "type": "string",
      "pattern": "^SPEC-[0-9]{4}$"
    },
    "estimated_input_tokens": { "type": "integer", "minimum": 0 },
    "estimated_output_tokens": { "type": "integer", "minimum": 0 },
    "estimated_cache_read_tokens": { "type": "integer", "minimum": 0 },
    "estimated_cache_write_tokens": { "type": "integer", "minimum": 0 },
    "estimated_usd": { "type": "number", "minimum": 0 },
    "confidence": { "type": "string", "enum": ["LOW", "MEDIUM", "HIGH"] },
    "model": { "type": "string" },
    "model_fallback": { "type": "boolean" },
    "n_data_points": { "type": "integer", "minimum": 0 },
    "budget_exceeded": { "type": "boolean" },
    "budget_limit_usd": { "type": "number", "minimum": 0 },
    "neighbors": {
      "type": "array",
      "maxItems": 3,
      "items": {
        "type": "object",
        "required": ["spec_id", "input_tokens", "output_tokens", "similarity"],
        "properties": {
          "spec_id": { "type": ["string", "null"] },
          "input_tokens": { "type": "integer", "minimum": 0 },
          "output_tokens": { "type": "integer", "minimum": 0 },
          "similarity": { "type": "number", "minimum": 0, "maximum": 1 }
        }
      }
    }
  },
  "additionalProperties": false
}
```

## Invarianten

- `confidence` ist exakt einer von: `LOW`, `MEDIUM`, `HIGH`
- `neighbors` enthält maximal 3 Einträge
- `similarity` liegt im Bereich [0.0, 1.0] (1.0 = identisch)
- Bei `--all` wird das Feld `estimates` als Array des obigen Schemas zurückgegeben:
  `{ "estimates": [ <EstimateResult>, ... ] }`
- `model_fallback: true` signalisiert, dass das Modell nicht in `model_prices` konfiguriert
  ist und auf `default` zurückgefallen wurde
