---
id: CON-0030
project: PRJ-0001
title: "Pipeline Phase State JSON Schema"
type: data
format: json-schema
spec: SPEC-0014
version: 0.1.0
status: draft
artifact: "contracts/data/pipeline-phase-state.schema.json"
tests: ["TST-0042"]
---

# Contract: Pipeline Phase State JSON Schema

> **Spec:** SPEC-0014 · **Typ:** Daten (JSON Schema) · **Status:** draft

## Zweck

Definiert die Erweiterung des bestehenden Pipeline-JSON-Formats
(`.sdd/pipeline/{timestamp}-{SPEC-ID}.json`) um die neuen Felder für den
Execution-Gate-Prozess. Dieser Contract **erweitert** das bestehende
Pipeline-JSON, bricht keine bestehenden Felder.

## Invarianten

- **INV-01:** `pipeline_phase` enthält immer die zuletzt **abgeschlossene** Phase
  (nicht die nächste). Wert `null` bedeutet: noch keine Phase abgeschlossen.
- **INV-02:** `phase_history` ist streng chronologisch — neuste Einträge am Ende.
- **INV-03:** Jedes `phase_history`-Element hat `phase`, `completed_at` und `result`.
- **INV-04:** `result` ist immer `ok` oder `failed`; kein anderer Wert.
- **INV-05:** `blocking_issues` ist leer wenn `pipeline_phase == execute-unlocked`.
- **INV-06:** Ein `override`-Eintrag ohne `reason` ist schema-invalid.

## Schema (neue Felder)

```json
{
  "spec_id": "SPEC-0014",
  "pipeline_phase": "contracts-proposed",
  "phase_history": [
    {
      "phase": "spec-draft",
      "completed_at": "2026-05-14T00:00:00Z",
      "result": "ok"
    },
    {
      "phase": "contracts-proposed",
      "completed_at": "2026-05-14T00:00:00Z",
      "result": "ok",
      "proposed": ["CON-0025", "CON-0026", "CON-0027", "CON-0028", "CON-0029", "CON-0030"]
    }
  ],
  "blocking_issues": [],
  "conflict_report_ref": null,
  "override": null
}
```

**Override-Objekt (wenn vorhanden):**

```json
{
  "override": {
    "triggered_at": "2026-05-14T15:00:00Z",
    "reason": "Hotfix: CF-0014-001 wird in SPEC-0015 adressiert",
    "blocked_phase": "contracts-review",
    "operator": "boris"
  }
}
```

## Feldspezifikation

| Feld | Typ | Pflicht | Beschreibung |
|------|-----|---------|--------------|
| `spec_id` | string | ja | SPEC-ID |
| `pipeline_phase` | string\|null | ja | Aktuell abgeschlossene Phase oder null |
| `phase_history` | array | ja | Chronologische Liste aller abgeschlossenen Phasen |
| `phase_history[].phase` | string | ja | Phasenname (s. Phasenmodell in CON-0025) |
| `phase_history[].completed_at` | string | ja | ISO-8601 Timestamp |
| `phase_history[].result` | enum | ja | `ok` \| `failed` |
| `blocking_issues` | string[] | ja | Textuell beschriebene Blocker (leer wenn ok) |
| `conflict_report_ref` | string\|null | nein | Pfad zum Konfliktbericht (relativ zum Repo-Root) |
| `override` | object\|null | nein | Ausgefüllt wenn --force verwendet wurde |
| `override.reason` | string | wenn override gesetzt | Begründung des Overrides (Pflicht) |
| `override.triggered_at` | string | wenn override gesetzt | ISO-8601 Timestamp |
| `override.blocked_phase` | string | wenn override gesetzt | Phase die übersprungen wurde |

## Validierung

- Schema unter `contracts/data/pipeline-phase-state.schema.json` (JSON Schema Draft 2020-12)
- Validatoren: `jsonschema` (Python), `ajv` (JS)
