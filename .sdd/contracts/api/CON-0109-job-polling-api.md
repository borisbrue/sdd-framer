---
id: CON-0109
project: PRJ-0001
title: Job-Status Polling API
type: api
format: markdown
spec: SPEC-0028
version: 0.1.0
status: review
tests:
- TST-0127
---
# Contract: Job-Status Polling API

## Garantie

`GET /api/specs/{spec_id}/job` gibt immer einen auswertbaren JSON-Status zurück — nie einen Fehler. Wenn kein Job läuft, ist `status: "idle"`.

## Endpunkt

### GET /api/specs/{spec_id}/job

Response wenn kein Job aktiv:
```json
{"spec_id": "SPEC-0028", "status": "idle"}
```

Response während Aktion läuft:
```json
{
  "spec_id": "SPEC-0028",
  "command": "review",
  "status": "running",
  "started_at": "2026-05-20T10:00:00+00:00",
  "output": "Analyzing spec...",
  "finished_at": null,
  "result": null
}
```

Response nach Abschluss:
```json
{
  "spec_id": "SPEC-0028",
  "command": "review",
  "status": "done",
  "started_at": "...",
  "output": "...",
  "finished_at": "2026-05-20T10:00:30+00:00",
  "result": { ... }
}
```

## Persistenz

Jobs werden in `.sdd/pipeline/{spec_id}-job.json` gespeichert. Ein neuer Job-Start überschreibt den vorherigen.

## Status-Werte

| Wert | Bedeutung |
|------|-----------|
| `idle` | Kein Job für diese Spec vorhanden |
| `running` | Aktion läuft gerade |
| `done` | Erfolgreich abgeschlossen |
| `failed` | Aktion ist fehlgeschlagen |
