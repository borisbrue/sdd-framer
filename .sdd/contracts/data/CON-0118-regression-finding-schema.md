---
id: CON-0118
project: ""                # PRJ-XXXX
title: "Regression Finding Schema"
type: data
format: json-schema
spec: SPEC-0030
version: 0.1.0
status: review
artifact: ".sdd/contracts/data/regression-finding-schema.schema.json"
tests: ["TST-0137"]
---

# Contract: Regression Finding Schema

> **Spec:** SPEC-0030 · **Typ:** Daten (JSON Schema) · **Status:** draft

## Zweck

Beschreibt das strukturierte Format eines einzelnen Regression-Befunds, wie er von
`sdd regression-check` ausgegeben wird (FR-03) und in `[rule]`/`[llm]`-Sektionen
der CLI-Ausgabe erscheint (FR-04). Wird als interne Datenstruktur und zur
maschinellen Weiterverarbeitung (z.B. in `/sdd-review`) verwendet.

## Invarianten

- **INV-01:** Pflichtfelder: `prefix`, `spec_id`, `section`, `own_section`, `type`, `severity`, `description` — kein Befund darf ein Pflichtfeld weglassen oder auf `null` setzen.
- **INV-02:** `type` ∈ {`overlap`, `conflict`, `redundancy`}
- **INV-03:** `severity` ∈ {`error`, `warning`, `info`}
- **INV-04:** `prefix` ∈ {`rule`, `llm`} — kennzeichnet die Prüfstufe des Befunds; ein Befund aus Stufe 1 hat immer `"prefix": "rule"`, aus Stufe 2 immer `"prefix": "llm"`.

## Beispiele

**Gültig:**
```json
{
  "prefix": "llm",
  "spec_id": "SPEC-0005",
  "section": "FR-03",
  "own_section": "FR-02",
  "type": "overlap",
  "severity": "warning",
  "description": "Beide Specs beschreiben Analyse-Session-Tracking mit gleicher Semantik."
}
```

**Ungültig (und warum):**
```json
{
  "prefix": "llm",
  "spec_id": "SPEC-0005",
  "severity": "critical"
}
```
→ Verstößt gegen INV-01 (`section`, `own_section`, `type`, `description` fehlen) und INV-03 (`"critical"` ist kein gültiger Severity-Wert).

## Validierung

- Schema unter `.sdd/contracts/data/regression-finding-schema.schema.json` (JSON Schema Draft 2020-12)
- Validatoren je nach Sprache: `ajv` (JS), `jsonschema` (Python), etc.
