---
id: CON-0044
project: PRJ-0001
title: "Schema der cost_estimation-Konfigurationssektion in config.yaml"
type: data
format: json-schema
spec: SPEC-0011
version: 0.1.0
status: review
artifact: "contracts/data/cost-estimation-config.schema.json"
tests:
- TST-0059
---

# Contract: Schema der `cost_estimation`-Konfiguration

> **Spec:** SPEC-0011 · **Typ:** Daten · **Status:** review

## Zweck

Definiert die erlaubte Struktur des `cost_estimation:`-Blocks in `.sdd/config.yaml`.

## Beispiel (Referenz-Konfiguration)

```yaml
cost_estimation:
  model_prices:
    claude-haiku-4-5-20251001:
      input_per_million: 0.80
      output_per_million: 4.00
      cache_write_per_million: 1.00
      cache_read_per_million: 0.08
    claude-sonnet-4-6:
      input_per_million: 3.00
      output_per_million: 15.00
      cache_write_per_million: 3.75
      cache_read_per_million: 0.30
    default:
      input_per_million: 3.00
      output_per_million: 15.00
      cache_write_per_million: 3.75
      cache_read_per_million: 0.30
  budget_alert_usd: 5.00
  default_model: claude-haiku-4-5-20251001
```

## Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "SDD Cost Estimation Config",
  "type": "object",
  "properties": {
    "model_prices": {
      "type": "object",
      "description": "Map von Modell-ID zu Preisangaben. 'default' als Fallback.",
      "additionalProperties": {
        "type": "object",
        "required": ["input_per_million", "output_per_million"],
        "properties": {
          "input_per_million":       { "type": "number", "minimum": 0 },
          "output_per_million":      { "type": "number", "minimum": 0 },
          "cache_write_per_million": { "type": "number", "minimum": 0 },
          "cache_read_per_million":  { "type": "number", "minimum": 0 }
        },
        "additionalProperties": false
      }
    },
    "budget_alert_usd": {
      "type": "number",
      "minimum": 0,
      "description": "Schwellwert in USD; Warnung wenn Schätzung ihn überschreitet. 0 = deaktiviert."
    },
    "default_model": {
      "type": "string",
      "description": "Fallback-Modell wenn --model nicht angegeben und Modell nicht in model_prices."
    }
  },
  "additionalProperties": false
}
```

## Invarianten

- Alle Preisangaben sind in USD pro 1 Million Tokens.
- `default`-Eintrag in `model_prices` wird verwendet wenn das angegebene Modell
  nicht in `model_prices` vorhanden ist.
- `budget_alert_usd: 0` oder fehlende Konfiguration → kein Budget-Alert.
- Änderungen hier beeinflussen nur die Kostendarstellung, nicht die Token-Schätzung selbst.
