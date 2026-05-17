---
id: CON-0029
project: PRJ-0001
title: "Conflict Report JSON Schema"
type: data
format: json-schema
spec: SPEC-0014
version: 0.1.0
status: draft
artifact: "contracts/data/conflict-report.schema.json"
tests: ["TST-0041"]
---

# Contract: Conflict Report JSON Schema

> **Spec:** SPEC-0014 · **Typ:** Daten (JSON Schema) · **Status:** draft

## Zweck

Definiert das Schema der Konfliktbericht-Datei, die von `sdd contract review`
(Phase 5) unter `.sdd/conflict-reports/{spec-id}-conflicts.json` geschrieben wird.
Konsumenten: CLI-Output-Renderer, Web UI Konfliktliste (CON-0027), Pipeline-Gate.

## Invarianten

- **INV-01:** Jeder Konflikt hat eine eindeutige `id` nach Schema `CF-{SPEC_NUM}-{NNN}`.
- **INV-02:** `severity` ist immer eines von `low | medium | high`.
- **INV-03:** `type` ist immer eines der 5 definierten Konflikttypen.
- **INV-04:** `status` startet als `open`; nur `resolved` und `acknowledged`
  gelten als "abgearbeitet".
- **INV-05:** `affected_specs` enthält mindestens die SPEC der `conflicting_contract`.
- **INV-06:** `impact_summary` wird aus den `conflicts`-Einträgen berechnet und
  muss konsistent sein (Summen stimmen, `affected_specs_count` = Kardinalität der
  Vereinigung aller `affected_specs`).

## Schema (kompakt)

```json
{
  "spec_id": "SPEC-0014",
  "generated_at": "2026-05-14T12:00:00Z",
  "new_contracts": ["CON-0025"],
  "conflicts": [
    {
      "id": "CF-0014-001",
      "type": "scope-overlap",
      "severity": "medium",
      "new_contract": "CON-0025",
      "conflicting_contract": "CON-0020",
      "detail": "CON-0020 INV-01 definiert Execute-Gate als 'status == approved'...",
      "affected_specs": ["SPEC-0007"],
      "required_action": "CON-0025 muss CON-0020 explizit erweitern (extend)",
      "status": "open",
      "resolution": null
    }
  ],
  "impact_summary": {
    "total_conflicts": 1,
    "high": 0,
    "medium": 1,
    "low": 0,
    "affected_specs_count": 1
  }
}
```

## Feldspezifikation

| Feld | Typ | Pflicht | Beschreibung |
|------|-----|---------|--------------|
| `spec_id` | string | ja | SPEC-ID des Berichts |
| `generated_at` | string (ISO-8601) | ja | Zeitpunkt der Analyse |
| `new_contracts` | string[] | ja | Neu geprüfte Contract-IDs |
| `conflicts[].id` | string | ja | `CF-{SPEC_NUM}-{NNN}` |
| `conflicts[].type` | enum | ja | Einer der 5 Konflikttypen |
| `conflicts[].severity` | enum | ja | `low` \| `medium` \| `high` |
| `conflicts[].new_contract` | string | ja | CON-ID des neuen Contracts |
| `conflicts[].conflicting_contract` | string | ja | CON-ID des bestehenden Contracts |
| `conflicts[].detail` | string | ja | Menschlich lesbare Konfliktbeschreibung |
| `conflicts[].affected_specs` | string[] | ja | SPECs die conflicting_contract referenzieren |
| `conflicts[].required_action` | string | nein | Empfohlene Lösung |
| `conflicts[].status` | enum | ja | `open` \| `resolved` \| `acknowledged` |
| `conflicts[].resolution` | object\|null | nein | Ausgefüllt nach resolve/acknowledge |

## Validierung

- Schema unter `contracts/data/conflict-report.schema.json` (JSON Schema Draft 2020-12)
- Validatoren: `jsonschema` (Python), `ajv` (JS)
