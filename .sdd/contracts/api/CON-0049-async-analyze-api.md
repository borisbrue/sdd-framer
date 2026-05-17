---
id: CON-0049
project: PRJ-0001
title: "Async Analyze API – Job-Start, Status-Poll, Verlauf & Dismiss"
type: api
format: openapi
spec: SPEC-0016
version: 0.1.0
status: draft
artifact: ""
tests: ["TST-0064"]
---

# Contract: Async Analyze API

> **Spec:** SPEC-0016 · **Typ:** API (OpenAPI) · **Status:** draft

## Zweck

Definiert die fünf neuen REST-Endpunkte für asynchrone, persistente KI-Analyse.
Der bestehende `PUT /api/docs/{doc_id}/analyze`-Endpunkt bleibt unverändert.

## Garantien

### G-01: POST /api/docs/{doc_id}/analyze/start

**Request:**
```json
{
  "content":       "# SPEC-0016\n...",
  "doc_type":      "spec",
  "dismissed_ids": ["q-001", "issue-002"],
  "session_id":    "sess-xyz"
}
```
`dismissed_ids` optional (default `[]`). `session_id` optional.

**Response 202:**
```json
{ "job_id": "3f8a1c2d-...", "status": "queued" }
```

**Fehler-Responses:**
| HTTP | Bedingung |
|------|-----------|
| 400 | `content` leer oder `doc_type` ungültig |
| 429 | Mehr als 5 gleichzeitige Jobs für denselben `doc_id` |

---

### G-02: GET /api/docs/{doc_id}/analyze/status/{job_id}

**Response 200 (laufend):**
```json
{ "status": "running", "result_id": null }
```

**Response 200 (fertig):**
```json
{ "status": "complete", "result_id": "2026-05-16T12:00:00_3f8a1c2d" }
```

**Response 200 (fehlgeschlagen):**
```json
{ "status": "failed", "result_id": null, "error": "LLM timeout after 120s" }
```

**Fehler-Responses:**
| HTTP | Bedingung |
|------|-----------|
| 404 | `job_id` unbekannt oder älter als 24 h |

---

### G-03: GET /api/docs/{doc_id}/analyses

Gibt die Liste aller persistierten Analysen für diesen Doc, neueste zuerst.
Limit: 50 Einträge.

**Response 200:**
```json
[
  {
    "result_id":      "2026-05-16T12:00:00_3f8a1c2d",
    "timestamp":      "2026-05-16T12:00:00Z",
    "question_count": 3,
    "issue_count":    1,
    "dismissed_count": 0
  }
]
```

Leere Liste `[]` wenn keine Analysen vorhanden (kein 404).

---

### G-04: GET /api/docs/{doc_id}/analyses/{result_id}

**Response 200:**
```json
{
  "result_id":    "2026-05-16T12:00:00_3f8a1c2d",
  "doc_id":       "SPEC-0016",
  "timestamp":    "2026-05-16T12:00:00Z",
  "session_id":   "sess-xyz",
  "dismissed_ids": ["q-001"],
  "questions":    [{ "id": "q-002", "section": "FR", "text": "...", "severity": "warning" }],
  "issues":       [{ "section": "FR", "text": "...", "severity": "error" }],
  "suggestions":  [{ "text": "..." }],
  "usage":        { "input_tokens": 1200, "output_tokens": 340 }
}
```

**Fehler-Responses:**
| HTTP | Bedingung |
|------|-----------|
| 404 | `result_id` nicht gefunden |

---

### G-05: PATCH /api/docs/{doc_id}/analyses/{result_id}/dismiss

**Request:**
```json
{ "item_id": "q-001", "dismissed": true }
```

`dismissed: false` reaktiviert das Item.

**Response 200:**
```json
{ "dismissed_ids": ["q-001"] }
```

**Fehler-Responses:**
| HTTP | Bedingung |
|------|-----------|
| 404 | `result_id` nicht gefunden |
| 400 | `item_id` leer |

## Invarianten

- **INV-01:** `job_id` ist ein UUID4-String, global eindeutig.
- **INV-02:** Jobs ohne Statusänderung seit ≥ 24 h werden aus dem Store gelöscht;
  `GET /status/{job_id}` antwortet dann mit 404.
- **INV-03:** `result_id` hat das Format `YYYY-MM-DDTHH:MM:SS_{job_id[:8]}`.
- **INV-04:** `dismissed_ids` in der persistierten Analyse wird in-place aktualisiert
  (kein neuer Analyse-Lauf).
- **INV-05:** Der Concurrent-Jobs-Limit (5 pro `doc_id`) basiert auf `status ∈ {queued, running}`.
- **INV-06:** Content wird auf 50 000 Zeichen gekürzt (identisch zum bestehenden Endpunkt).

## Begriffe

| Begriff | Definition |
|---------|-----------|
| `job_id` | UUID4-String, identifiziert einen Analyse-Job im Speicher |
| `result_id` | Dateiname ohne Extension; identifiziert eine persistierte Analyse |
| `dismissed_ids` | Liste von Item-IDs (questions/issues/suggestions), die beim nächsten Analyse-Lauf aus dem Prompt gefiltert werden |
