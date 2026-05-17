---
id: CON-0050
project: PRJ-0001
title: "Persisted Analysis – JSON-Datenschema"
type: data
format: json-schema
spec: SPEC-0016
version: 0.1.0
status: draft
artifact: ""
tests: ["TST-0065"]
---

# Contract: Persisted Analysis JSON Schema

> **Spec:** SPEC-0016 · **Typ:** Data · **Status:** draft

## Zweck

Definiert das JSON-Schema einer persistierten Analyse-Datei unter
`.sdd/analyses/{doc_id}/{YYYY-MM-DDTHH:MM:SS}_{job_id[:8]}.json`.

## Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "PersistedAnalysis",
  "type": "object",
  "required": ["result_id", "doc_id", "timestamp", "session_id",
               "dismissed_ids", "questions", "issues", "suggestions", "usage"],
  "additionalProperties": false,
  "properties": {
    "result_id":     { "type": "string", "minLength": 1 },
    "doc_id":        { "type": "string", "minLength": 1 },
    "timestamp":     { "type": "string", "format": "date-time" },
    "session_id":    { "type": "string" },
    "dismissed_ids": {
      "type": "array",
      "items": { "type": "string" },
      "uniqueItems": true
    },
    "questions": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id", "section", "text", "severity"],
        "properties": {
          "id":       { "type": "string" },
          "section":  { "type": "string" },
          "text":     { "type": "string" },
          "severity": { "type": "string", "enum": ["error", "warning", "suggestion"] }
        }
      }
    },
    "issues": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["section", "text", "severity"],
        "properties": {
          "section":  { "type": "string" },
          "text":     { "type": "string" },
          "severity": { "type": "string", "enum": ["error", "warning", "suggestion"] }
        }
      }
    },
    "suggestions": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["text"],
        "properties": {
          "text": { "type": "string" }
        }
      }
    },
    "usage": {
      "type": "object",
      "required": ["input_tokens", "output_tokens"],
      "properties": {
        "input_tokens":       { "type": "integer", "minimum": 0 },
        "output_tokens":      { "type": "integer", "minimum": 0 },
        "cache_read_tokens":  { "type": "integer", "minimum": 0 },
        "cache_write_tokens": { "type": "integer", "minimum": 0 }
      }
    }
  }
}
```

## Invarianten

- **INV-01:** `result_id` entspricht dem Dateinamen ohne Extension.
- **INV-02:** `timestamp` ist ein ISO-8601-String mit Zeitzone (UTC empfohlen).
- **INV-03:** `dismissed_ids` enthält keine Duplikate (`uniqueItems: true`).
- **INV-04:** Ein Item in `dismissed_ids` muss nicht zwingend als `id` in `questions`
  existieren — beim Filtern werden unbekannte IDs ignoriert.
- **INV-05:** `additionalProperties: false` — keine undokumentierten Felder erlaubt.

## Dateipfad-Konvention

```
.sdd/analyses/{doc_id}/{YYYY-MM-DDTHH:MM:SS}_{job_id[:8]}.json
```

Beispiel: `.sdd/analyses/SPEC-0016/2026-05-16T12:00:00_3f8a1c2d.json`

`doc_id` wird als Verzeichnisname verwendet; Zeichen die in Dateinamen ungültig sind
(`/`, `\`, `:`) werden durch `_` ersetzt.
