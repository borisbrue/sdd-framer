---
id: CON-0141
project: ""
title: "SSE-Endpoint GET /orchestrate/stream/{run_id}"
type: api
format: openapi
spec: SPEC-0037
version: 0.1.0
status: deprecated
artifact: "tool/sdd_cli/web/api/routes/dag_monitor.py"
tests: ["TST-0165"]
deprecated_reason: "mit SPEC-0037 abgelöst: Autopilot nie lauffähig; der Monitor liest seit SPEC-0058 das Pipeline-Protokoll"
---

# Contract: SSE-Endpoint /orchestrate/stream/{run_id}

> **Spec:** SPEC-0037 · **Typ:** API · **Status:** approved

## Zweck

Der SSE-Endpoint streamt `DagEvent`-Objekte für einen laufenden Run an die WebUI
(FR-02). Erweitert den bestehenden SSE-Kanal aus SPEC-0007 auf Task-Granularität.

## Invarianten

- **INV-01:** Response `Content-Type` ist `text/event-stream`.
- **INV-02:** Jedes SSE-Event enthält ein JSON-kodiertes `DagEvent`-Objekt im
  `data:`-Feld.
- **INV-03:** Der Endpoint sendet alle 15 s einen Heartbeat-Comment (`: heartbeat`)
  um die Verbindung aktiv zu halten (`dag_monitor.sse_heartbeat_seconds`).
- **INV-04:** Bei unbekannter `run_id` wird die SSE-Verbindung geöffnet und wartet
  (kein 404) — der Client kann auch vor dem Start des Runs subscriben.
- **INV-05:** Nach `DagEventBus.close(run_id)` beendet der Endpoint den Stream
  sauber ohne hängende Verbindung.
