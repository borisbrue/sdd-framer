---
id: CON-0051
project: PRJ-0001
title: "AnalysisJob – In-Memory-Datenstruktur"
type: data
format: dataclass
spec: SPEC-0016
version: 0.1.0
status: draft
artifact: ""
tests: ["TST-0066"]
---

# Contract: AnalysisJob In-Memory Schema

> **Spec:** SPEC-0016 · **Typ:** Data · **Status:** draft

## Zweck

Definiert die Datenstruktur eines `AnalysisJob`-Objekts, das im `JobStore`
(In-Memory-Dict) gehalten wird. Kein Datenbankschema — Jobs überleben keinen
Prozess-Neustart.

## Python-Dataclass

```python
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class AnalysisJob:
    job_id:     str           # UUID4-String
    doc_id:     str           # z.B. "SPEC-0016"
    status:     str           # "queued" | "running" | "complete" | "failed"
    result_id:  str | None    # gesetzt wenn status == "complete"
    error:      str | None    # gesetzt wenn status == "failed"
    created_at: datetime      # UTC, für TTL-Cleanup
    updated_at: datetime      # UTC, für TTL-Cleanup
```

## Invarianten

- **INV-01:** `status` ist immer eines von `{"queued", "running", "complete", "failed"}`.
- **INV-02:** `result_id` ist `None` solange `status != "complete"`.
- **INV-03:** `error` ist `None` solange `status != "failed"`.
- **INV-04:** `created_at` und `updated_at` sind UTC-Timestamps.
- **INV-05:** Ein Job mit `updated_at` älter als 24 h wird vom `JobStore` beim
  nächsten Cleanup-Durchlauf entfernt.
- **INV-06:** `job_id` ist eindeutig über alle aktiven Jobs des Prozesses.

## JobStore-Interface

```python
class JobStore:
    def create(self, doc_id: str) -> AnalysisJob: ...
    def get(self, job_id: str) -> AnalysisJob | None: ...
    def update_running(self, job_id: str) -> None: ...
    def update_complete(self, job_id: str, result_id: str) -> None: ...
    def update_failed(self, job_id: str, error: str) -> None: ...
    def active_count(self, doc_id: str) -> int: ...   # status in {queued, running}
    def cleanup_expired(self) -> int: ...              # returns count removed
```

## Concurrent-Jobs-Throttle

`active_count(doc_id)` zählt Jobs mit `status ∈ {queued, running}` für den
gegebenen `doc_id`. Wenn `active_count >= 5`, antwortet `POST /analyze/start` mit HTTP 429.
