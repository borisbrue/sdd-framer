---
id: CON-0075
title: "sdd-run-api"
type: api
format: openapi
spec: SPEC-0023
version: 0.1.0
status: draft
tests: [TST-0106]
---

# Contract: POST /api/sdd/run

> **Spec:** SPEC-0023 · **Typ:** API · **Status:** draft

## Zweck

Führt einen beliebigen `sdd`-Command als Subprocess aus und streamt den Output
via Server-Sent Events. Nach Abschluss wird optional eine Push-Notification gesendet.

## Garantien

| ID | Garantie |
|---|---|
| G-01 | Auth: `Authorization: Bearer <token>`. Fehlt / falsch → HTTP 401 |
| G-02 | Request-Body: `{"cmd": "orchestrate", "args": ["SPEC-0024"]}` — `cmd` ist Pflicht, `args` optional |
| G-03 | Unbekannter Command (nicht in Allowlist) → HTTP 422 mit `detail: "unknown_command"` |
| G-04 | SSE-Event pro Zeile: `data: {"type": "line", "data": "...", "stream": "stdout"\|"stderr"}` |
| G-05 | Abschluss-Event: `data: {"type": "done", "exit_code": 0\|-1}` |
| G-06 | Bei Abschluss: PushStore.broadcast wird aufgerufen wenn cmd in Push-Trigger-Liste |
| G-07 | Push-Trigger-Commands: `orchestrate`, `dev` (alle Sub-Commands) |
| G-08 | Content-Type der Response: `text/event-stream` |
| G-09 | Command-Allowlist: `orchestrate`, `start`, `validate`, `dev`, `contract`, `spec`, `estimate` |

## Request-Body

```json
{"cmd": "orchestrate", "args": ["--spec", "SPEC-0024"]}
```

## SSE-Format

```
data: {"type": "line", "data": "✓ Contracts geladen...", "stream": "stdout"}
data: {"type": "line", "data": "Build fehlgeschlagen", "stream": "stderr"}
data: {"type": "done", "exit_code": 0}
```

## Endpoint

```
POST /api/sdd/run
Authorization: Bearer <token>
Content-Type: application/json
Response: 200 text/event-stream
Response: 401 {"detail": "invalid_token"}
Response: 422 {"detail": "unknown_command"}
```
