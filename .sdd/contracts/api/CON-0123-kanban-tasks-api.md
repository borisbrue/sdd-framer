---
id: CON-0123
project: ""
title: "Kanban Tasks API – GET /api/specs/{spec_id}/tasks + SSE /events"
type: api
format: openapi
spec: SPEC-0034
version: 0.1.0
status: draft
artifact: ".sdd/contracts/api/kanban-tasks-api.openapi.yaml"
tests: ["TST-0144"]
---

# Contract: Kanban Tasks API

> **Spec:** SPEC-0034 · **Typ:** API (OpenAPI) · **Status:** draft

## Zweck

Definiert zwei neue Endpunkte unter `/api/specs/{spec_id}/`:

- `GET /api/specs/{spec_id}/tasks` — gibt alle Tasks des letzten Runs zurück (FR-01)
- `GET /api/specs/{spec_id}/tasks/events` — SSE-Stream für Echtzeit-Task-Updates (FR-02)

Diese Endpunkte sind der einzige Kommunikationskanal zwischen Web UI und dem
Task-Kanban-Board. Die Daten kommen aus `.sdd/runs/{spec_id}/{run_id}/tasks.json`
(Repository-Pattern, vgl. SPEC-0034 Pattern-Register).

## Garantien

### G-01: GET /api/specs/{spec_id}/tasks

**Response 200:**
```json
{
  "spec_id": "SPEC-0034",
  "run_id": "run-20260603-001",
  "tasks": [
    {
      "id": "uuid-v4",
      "title": "string",
      "description": "string",
      "type": "code|test|config|doc",
      "status": "pending|assigned|running|review|passed|failed|committed|retrying|blocked",
      "complexity": "low|medium|high",
      "context_size": "S|M|L",
      "estimated_tokens": 1500,
      "actual_tokens": null,
      "llm_id": null,
      "parallel_group": "group-1",
      "dependencies": [],
      "test_ids": ["TST-0144"],
      "error_context": []
    }
  ]
}
```

**Invarianten:**
- INV-01: `estimated_tokens` ist immer > 0 (wird beim Decompose gesetzt)
- INV-02: `actual_tokens` ist `null` solange der Task noch nicht `committed` oder `failed` ist
- INV-03: `parallel_group` ist `null` oder ein nicht-leerer String
- INV-04: Gibt `{"spec_id": "...", "run_id": null, "tasks": []}` zurück wenn kein Run existiert (kein 404)
- INV-05: Gibt immer den letzten Run zurück (höchste `run_id` in `.sdd/runs/{spec_id}/`)

**Response 200 (kein Run vorhanden):**
```json
{"spec_id": "SPEC-0034", "run_id": null, "tasks": []}
```

### G-02: GET /api/specs/{spec_id}/tasks/events (SSE)

**Content-Type:** `text/event-stream`

**Event-Format:**
```
event: task_update
data: {"run_id": "run-20260603-001", "timestamp": "2026-06-03T10:00:00Z", "task": {<vollständiges Task-Objekt>}}

event: run_started
data: {"run_id": "run-20260603-001", "spec_id": "SPEC-0034", "timestamp": "2026-06-03T10:00:00Z"}

event: run_completed
data: {"run_id": "run-20260603-001", "spec_id": "SPEC-0034", "timestamp": "2026-06-03T10:05:00Z"}
```

**Invarianten:**
- INV-06: Jedes `task_update`-Event enthält das vollständige Task-Objekt (nicht nur das Delta)
- INV-07: Events treffen innerhalb 500 ms nach Statuswechsel ein (SLO)
- INV-08: `run_id` und `timestamp` sind in jedem Event vorhanden (für Tracing)
- INV-09: Stream sendet ein `run_completed`-Event wenn alle Tasks `committed` oder `blocked` sind
- INV-10: Wenn kein Run aktiv ist, wartet der Stream auf den nächsten `run_started`-Event

## Fehlerfälle

| HTTP-Status | Bedingung |
|------------|-----------|
| 404 | `spec_id` existiert nicht im Projekt |
| 503 | SSE-Stream nicht verfügbar (Fallback auf Polling empfohlen) |
