---
id: CON-0140
project: ""
title: "DagEvent Schema"
type: data
format: json-schema
spec: SPEC-0037
version: 0.1.0
status: approved
artifact: "tool/sdd_cli/dag_event.py"
tests: ["TST-0162"]
---

# Contract: DagEvent Schema

> **Spec:** SPEC-0037 · **Typ:** Daten (Pydantic) · **Status:** approved

## Zweck

Definiert das Schema für `DagEvent`-Objekte, die vom `DagScheduler` (SPEC-0036)
in den `DagEventBus` publiziert werden und per SSE an die WebUI gestreamt werden
(FR-02, Pattern Observer §3).

## Invarianten

- **INV-01:** `run_id` und `task_id` sind Pflichtfelder (nicht leer).
- **INV-02:** `status` ist eines von: `pending`, `running`, `done`, `failed`,
  `skipped`, `paused` — keine anderen Werte zulässig.
- **INV-03:** `timestamp` wird automatisch auf `datetime.utcnow()` gesetzt wenn
  nicht explizit übergeben.
- **INV-04:** Events verschiedener `run_id`-Werte sind vollständig isoliert —
  ein Subscriber auf `run_id="A"` empfängt keine Events von `run_id="B"`.
- **INV-05:** `DagEventBus.publish()` darf nicht blockieren; Aufrufe ohne aktiven
  Subscriber werfen keine Exception.
