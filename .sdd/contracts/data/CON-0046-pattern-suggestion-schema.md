---
id: CON-0046
project: PRJ-0001
title: "Pattern Suggestion Schema"
type: data
format: json-schema
spec: SPEC-0015
version: 0.1.0
status: review
artifact: ".sdd/contracts/data/pattern-suggestion-schema.schema.json"
tests: ["TST-0002"]
---

# Contract: Pattern Suggestion Schema

> **Spec:** SPEC-0015 · **Typ:** Daten (JSON Schema) · **Status:** review

## Zweck

Definiert das Ausgabe-Format der Pattern-Vorschläge, die der LLM beim `sdd spec review`
(Phase 2c) und `sdd contract review` (Phase 5c) sowie dem eigenständigen Befehl
`sdd pattern-suggest` erzeugt. Jeder Vorschlag verweist auf den Refactoring Guru Katalog
und enthält eine Begründung sowie eine abgelehnte Alternative.

## Invarianten

- **INV-01:** Jeder Vorschlag enthält `pattern_name` (nicht leer), `category` ∈ {Creational, Structural, Behavioral}, `refactoring_guru_url` (beginnt mit "https://refactoring.guru/"), `applies_to` (nicht leer), `rationale` (nicht leer), `alternative` (nicht leer), `effort` ∈ {low, medium, high}, `priority` ∈ {recommended, optional, consider}.
- **INV-02:** `pattern_suggestions` ist ein Array mit 0–4 Einträgen (nie mehr als 4 Vorschläge pro Artefakt).
- **INV-03:** Zwei Einträge im selben Ergebnis dürfen nicht dasselbe `pattern_name` enthalten.
- **INV-04:** `refactoring_guru_url` ist eine gültige HTTPS-URL (Format validierbar per Regex `^https://refactoring\.guru/.*`).

## JSON Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "PatternSuggestionResult",
  "type": "object",
  "required": ["artifact_id", "artifact_type", "generated_at", "pattern_suggestions"],
  "additionalProperties": false,
  "properties": {
    "artifact_id": { "type": "string", "pattern": "^(SPEC|CON)-[0-9]{4,}$" },
    "artifact_type": { "type": "string", "enum": ["spec", "contract"] },
    "generated_at": { "type": "string", "description": "ISO 8601 UTC" },
    "pattern_suggestions": {
      "type": "array",
      "minItems": 0,
      "maxItems": 4,
      "uniqueItems": true,
      "items": {
        "type": "object",
        "required": ["pattern_name", "category", "refactoring_guru_url", "applies_to", "rationale", "alternative", "effort", "priority"],
        "additionalProperties": false,
        "properties": {
          "pattern_name":          { "type": "string", "minLength": 1 },
          "category":              { "type": "string", "enum": ["Creational", "Structural", "Behavioral"] },
          "refactoring_guru_url":  { "type": "string", "pattern": "^https://refactoring\\.guru/" },
          "applies_to":            { "type": "string", "minLength": 1 },
          "rationale":             { "type": "string", "minLength": 10 },
          "alternative":           { "type": "string", "minLength": 10 },
          "effort":                { "type": "string", "enum": ["low", "medium", "high"] },
          "priority":              { "type": "string", "enum": ["recommended", "optional", "consider"] }
        }
      }
    }
  }
}
```

## Beispiele

**Gültig:**
```json
{
  "artifact_id": "SPEC-0015",
  "artifact_type": "spec",
  "generated_at": "2026-05-15T10:00:00Z",
  "pattern_suggestions": [
    {
      "pattern_name": "Strategy",
      "category": "Behavioral",
      "refactoring_guru_url": "https://refactoring.guru/design-patterns/strategy",
      "applies_to": "SPEC-0015 / SolidChecker-Implementierung",
      "rationale": "Jedes SOLID-Prinzip ist ein unabhängiger Algorithmus mit gleichem Interface. Strategy erlaubt unabhängiges Testen und Austauschen ohne Änderung am Aufrufer.",
      "alternative": "Template Method – abgelehnt: Checker teilen keine gemeinsame Algorithmus-Struktur, nur das Interface ist gemeinsam.",
      "effort": "low",
      "priority": "recommended"
    }
  ]
}
```

**Ungültig (und warum):**
```json
{
  "artifact_id": "SPEC-0015",
  "artifact_type": "spec",
  "generated_at": "2026-05-15T10:00:00Z",
  "pattern_suggestions": [
    {
      "pattern_name": "Strategy",
      "category": "Unknown",
      "refactoring_guru_url": "http://refactoring.guru/strategy",
      "applies_to": "",
      "rationale": "gut",
      "alternative": "nein",
      "effort": "fast",
      "priority": "maybe"
    }
  ]
}
```
→ Verletzt INV-01: `category` nicht in Enum, URL kein HTTPS, `applies_to` leer, `rationale` zu kurz, `effort`/`priority` ungültige Werte.

## Validierung

Schema unter `.sdd/contracts/data/pattern-suggestion-schema.schema.json` (JSON Schema Draft 2020-12).
Validatoren: `jsonschema` (Python), `ajv` (JS).
