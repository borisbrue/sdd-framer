---
id: CON-0021
project: ""
title: "Orchestrate API – POST /api/orchestrate + GET /api/pipeline/{run_id}"
type: api
format: openapi
spec: SPEC-0007
version: 0.4.0
status: active
artifact: "contracts/api/orchestrate-api.openapi.yaml"
tests: ["TST-0025"]
---

# Contract: Orchestrate API

> **Spec:** SPEC-0007 · **Typ:** API (OpenAPI) · **Status:** draft

## Zweck

Definiert die zwei neuen REST-Endpunkte, die den Execute-Flow aus der
Web UI ermöglichen: Pipeline-Start und Status-Polling.

## Garantien

### G-01: POST /api/orchestrate

**Request:**
```json
{
  "spec_id":    "SPEC-0007",
  "project_id": "PRJ-0001",
  "dry_run":    false,
  "no_pr":      false,
  "base_url":   "http://localhost:8000"
}
```

Pflichtfeld: `spec_id`. `project_id` optional — Backend liest Fallback aus
Spec-Frontmatter (`spec.project`). Alle anderen Felder optional mit Defaults.

**Response 202:**
```json
{
  "run_id": "SPEC-0007-1747084800000"
}
```

**Fehler-Responses:**
| HTTP | Bedingung                                              |
|------|--------------------------------------------------------|
| 404  | Spec nicht gefunden                                    |
| 422  | `status != approved`                                   |
| 409  | Lauf für diese Spec-ID bereits aktiv                   |
| 409  | `pipeline_phase != execute-unlocked` (Gate nicht bestanden) — Response-Body enthält `gate_status` mit Phasenübersicht. Ausnahme: Request enthält `"force": true` mit `"override_reason"` (≥1 Zeichen), dann wird der Lauf gestartet und der Override im Pipeline-JSON protokolliert. |

### G-02: GET /api/pipeline/{run_id}

**Response 200 (laufend):**
```json
{
  "run_id":       "SPEC-0007-1747084800000",
  "spec_id":      "SPEC-0007",
  "status":       "running",
  "current_step": "Code wird generiert… (Attempt 1/3)",
  "attempts":     []
}
```

**Response 200 (abgeschlossen — Erfolg):**
```json
{
  "run_id":   "SPEC-0007-1747084800000",
  "spec_id":  "SPEC-0007",
  "status":   "labeled",
  "attempts": [
    {
      "attempt":       1,
      "branch":        "sdd/SPEC-0007-attempt-1",
      "build_passed":  true,
      "eval_pass_rate": 0.95,
      "pr_url":        "https://github.com/org/repo/pull/42",
      "error":         null,
      "explanation":   "implement guided spec creation analyze endpoint"
    }
  ]
}
```

**Response 200 (abgeschlossen — Fehlschlag):**
```json
{
  "run_id":    "SPEC-0007-1747084800000",
  "spec_id":   "SPEC-0007",
  "status":    "failed",
  "attempts":  [ { "attempt": 3, "eval_pass_rate": 0.6, "error": "…", "pr_url": "…" } ],
  "issue_url": "https://github.com/org/repo/issues/7"
}
```

**Fehler-Responses:**
| HTTP | Bedingung                    |
|------|------------------------------|
| 404  | `run_id` nicht gefunden      |

### G-03: GET /api/pipeline/active

**Query-Parameter:** `spec_id` (Pflicht)

**Response 200:**
```json
{
  "run_id":       "SPEC-0007-1747084800000",
  "spec_id":      "SPEC-0007",
  "status":       "running",
  "current_step": "Code wird generiert… (Attempt 1/3)"
}
```

**Response 404:** Kein aktiver Lauf für diese `spec_id`.

Gibt nur Läufe zurück die aktuell `status == running` haben.
Abgeschlossene Runs sind über G-02 abrufbar.

## Invarianten

- **INV-01:** `run_id` ist global eindeutig für die Lebensdauer des
  API-Prozesses.
- **INV-02:** Ein abgeschlossener Run bleibt mindestens 1 Stunde abrufbar
  (TTL im In-Memory-Store).
- **INV-03:** `status` ist immer eines von:
  `running | labeled | merged | failed | dry_run`.
- **INV-04:** `current_step` ist nur befüllt wenn `status == running`;
  bei Endzuständen ist das Feld leer oder absent.
- **INV-05:** `POST /api/orchestrate` gibt HTTP 503 zurück wenn `claude` CLI
  nicht im PATH oder nicht eingeloggt ist.
- **INV-06:** `project_id` im Request-Body überschreibt den Wert aus dem
  Spec-Frontmatter; fehlt beides, wird leerer String an `run_pipeline()` übergeben.
- **INV-07:** `POST /api/orchestrate` gibt HTTP 409 zurück wenn
  `pipeline_phase != execute-unlocked`, es sei denn der Request enthält
  `"force": true` und `"override_reason"` mit einem nicht-leeren String.
  Ein Force-Override wird im Pipeline-JSON protokolliert (CON-0025, CON-0030).

## Begriffe

| Begriff      | Definition                                                              |
|--------------|-------------------------------------------------------------------------|
| run_id       | `{spec_id}-{unix_timestamp_ms}` — eindeutige Pipeline-Run-Kennung      |
| current_step | Menschenlesbarer Fortschritts-Text, aktualisiert vom Background-Worker |
| issue_url    | GitHub-Issue-URL, nur befüllt wenn `status == failed`                  |

## Seit SPEC-0062 (0.4.0)

Die Route ist ein Adapter vor `sdd pipeline run SPEC --auto` (CON-0216): `run_id` ist die Run-ID der
Pipeline (`.sdd/runs/<SPEC>/<run_id>`). Neu im Schema: Status `paused` (Run wartet auf eine
Session-Rolle) und `aborted`, die Felder `max_attempts`, `log` und `report` sowie die Routen
`POST /api/pipeline/{run_id}/abort` und `GET /api/pipeline/{run_id}/log` (SSE), die der Code schon
vorher anbot.
