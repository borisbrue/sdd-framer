---
id: CON-0047
project: PRJ-0001
title: "Pattern Registry Schema"
type: data
format: json-schema
spec: SPEC-0015
version: 0.1.0
status: review
artifact: ".sdd/contracts/data/pattern-registry-schema.schema.json"
tests: ["TST-0062"]
---

# Contract: Pattern Registry Schema

> **Spec:** SPEC-0015 · **Typ:** Daten (JSON Schema) · **Status:** review

## Zweck

Definiert das Format der Pattern-Register-Dateien unter `.sdd/patterns/`.
Es gibt zwei Arten:
- **`SPEC-XXXX-patterns.json`** – Alle Pattern-Entscheidungen für eine spezifische SPEC
- **`_catalog.json`** – Aggregierter Überblick aller akzeptierten Patterns im Projekt

Pattern-Entscheidungen werden nach `sdd pattern-accept` oder `sdd pattern-reject`
in die SPEC-spezifische Datei geschrieben und im Catalog aggregiert.

## Invarianten

- **INV-01:** Jeder `pattern`-Eintrag enthält `pattern_name` (nicht leer), `status` ∈ {accepted, rejected, under-review}, `decided_at` (ISO 8601, nicht null wenn status accepted/rejected).
- **INV-02:** `rejection_reason` ist `null` wenn `status` = accepted; muss gesetzt sein (nicht leer) wenn `status` = rejected.
- **INV-03:** `acceptance_reason` ist `null` wenn `status` = rejected; muss gesetzt sein (nicht leer) wenn `status` = accepted.
- **INV-04:** Innerhalb einer SPEC-Datei ist `pattern_name` eindeutig (kein Duplikat).
- **INV-05:** `_catalog.json` enthält nur Patterns mit `status: accepted`.
- **INV-06:** Ein SPEC-Patterns-Dateiname folgt dem Muster `SPEC-[0-9]{4,}-patterns.json`.

## JSON Schema (SPEC-spezifisch)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "SpecPatternRegistry",
  "type": "object",
  "required": ["spec_id", "generated_at", "patterns"],
  "additionalProperties": false,
  "properties": {
    "spec_id":       { "type": "string", "pattern": "^SPEC-[0-9]{4,}$" },
    "generated_at":  { "type": "string", "description": "ISO 8601 UTC" },
    "patterns": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["pattern_name", "status"],
        "additionalProperties": false,
        "properties": {
          "pattern_name":      { "type": "string", "minLength": 1 },
          "status":            { "type": "string", "enum": ["accepted", "rejected", "under-review"] },
          "decided_at":        { "type": ["string", "null"] },
          "acceptance_reason": { "type": ["string", "null"] },
          "rejection_reason":  { "type": ["string", "null"] },
          "refactoring_guru_url": { "type": ["string", "null"] }
        }
      }
    }
  }
}
```

## JSON Schema (Catalog)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "PatternCatalog",
  "type": "object",
  "required": ["last_updated", "accepted_patterns"],
  "additionalProperties": false,
  "properties": {
    "last_updated": { "type": "string" },
    "accepted_patterns": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["pattern_name", "spec_id", "accepted_at"],
        "additionalProperties": false,
        "properties": {
          "pattern_name":         { "type": "string" },
          "spec_id":              { "type": "string", "pattern": "^SPEC-[0-9]{4,}$" },
          "accepted_at":          { "type": "string" },
          "acceptance_reason":    { "type": ["string", "null"] },
          "refactoring_guru_url": { "type": ["string", "null"] }
        }
      }
    }
  }
}
```

## Beispiele

**SPEC-0015-patterns.json (gültig):**
```json
{
  "spec_id": "SPEC-0015",
  "generated_at": "2026-05-15T10:00:00Z",
  "patterns": [
    {
      "pattern_name": "Strategy",
      "status": "accepted",
      "decided_at": "2026-05-15T10:05:00Z",
      "acceptance_reason": "Jeder SOLID-Checker ist ein unabhängiger Algorithmus mit gleichem Interface.",
      "rejection_reason": null,
      "refactoring_guru_url": "https://refactoring.guru/design-patterns/strategy"
    },
    {
      "pattern_name": "TemplateMethod",
      "status": "rejected",
      "decided_at": "2026-05-15T10:06:00Z",
      "acceptance_reason": null,
      "rejection_reason": "Checker teilen keine gemeinsame Algorithmus-Basis-Struktur.",
      "refactoring_guru_url": "https://refactoring.guru/design-patterns/template-method"
    }
  ]
}
```

**Ungültig (INV-02 verletzt):**
```json
{
  "patterns": [
    {
      "pattern_name": "Strategy",
      "status": "rejected",
      "rejection_reason": null
    }
  ]
}
```
→ `rejection_reason` muss gesetzt sein wenn `status: rejected`.

## Validierung

Schema unter `.sdd/contracts/data/pattern-registry-schema.schema.json` (JSON Schema Draft 2020-12).
Validatoren: `jsonschema` (Python), `ajv` (JS).
