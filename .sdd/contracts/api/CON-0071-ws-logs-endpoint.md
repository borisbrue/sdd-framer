---
id: CON-0071
title: "ws-logs-endpoint"
type: api
format: openapi
spec: SPEC-0022
version: 0.1.0
status: draft
artifact: "contracts/api/ws-logs-endpoint.openapi.yaml"
tests: [TST-0082]
---

# Contract: ws-logs-endpoint

> **Spec:** SPEC-0022 · **Typ:** API (WebSocket/OpenAPI) · **Status:** draft

## Zweck

Definiert den WebSocket-Endpoint `/ws/logs/{spec_id}` für Live Container-Logs
im SDD Web UI.

## Garantien

- **G-01:** Der Endpoint akzeptiert WebSocket-Verbindungen auf `/ws/logs/{spec_id}`.
- **G-02:** Jede gesendete Nachricht ist eine JSON-Zeile:
  `{"ts": "<ISO8601>", "line": "<log-zeile>", "spec_id": "<SPEC-ID>"}`.
- **G-03:** Beim Verbindungsaufbau werden zuerst die Buffer-History-Zeilen gesendet
  (mit `"buffered": true`), danach Live-Zeilen (ohne `"buffered"`).
- **G-04:** Wenn `spec_id` nicht existiert oder kein LogStreamer aktiv ist, sendet
  der Server `{"error": "no_stream", "spec_id": "<SPEC-ID>"}` und schließt die
  Verbindung.

## Nachrichtenformat

```json
{
  "ts": "2026-05-17T10:00:00.123Z",
  "line": "pytest: 12 passed in 0.4s",
  "spec_id": "SPEC-0022",
  "buffered": false
}
```

## Invarianten

- **INV-01:** `spec_id` im Pfad muss dem Format `SPEC-[0-9]{4}` entsprechen —
  andere Werte: HTTP 400 vor dem WebSocket-Upgrade.
- **INV-02:** Der Server sendet kein Ping/Pong — Clients sind für Keep-Alive
  verantwortlich.
- **INV-03:** Maximale Message-Größe: 4 KB pro Log-Zeile (längere Zeilen werden
  auf 4 KB gekürzt + `"truncated": true` hinzugefügt).
