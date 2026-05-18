---
id: CON-0077
title: "push-notification-payload"
type: data
format: json-schema
spec: SPEC-0023
version: 0.1.0
status: draft
tests: [TST-0108]
---

# Contract: Push-Notification-Payload

> **Spec:** SPEC-0023 · **Typ:** Data Schema · **Status:** draft

## Zweck

Definiert das JSON-Schema für den Inhalt jeder Push-Notification.
Wird sowohl vom Backend (PushStore.broadcast) als auch vom Client-seitigen
Service Worker (CON-0092) konsumiert.

## Schema

```typescript
interface PushPayload {
  type: "orchestrate_done" | "build_done" | "build_failed" | "spec_implemented";
  spec_id: string;   // z.B. "SPEC-0024" — Spec die den Event ausgelöst hat
  message: string;   // menschenlesbar, z.B. "SPEC-0024 — Pipeline abgeschlossen"
}
```

## Garantien

| ID | Garantie |
|---|---|
| G-01 | `type` ist immer einer der vier definierten Werte |
| G-02 | `spec_id` entspricht dem Format `SPEC-XXXX` (4 Ziffern) |
| G-03 | `message` ist niemals leer |
| G-04 | JSON-Größe ≤ 4096 Bytes (Web Push API Limit) |
| G-05 | Payload-Encoding: UTF-8 JSON-String |

## Beispiele

```json
{"type": "orchestrate_done", "spec_id": "SPEC-0024", "message": "SPEC-0024 — Pipeline abgeschlossen (approved)"}
{"type": "build_failed", "spec_id": "SPEC-0024", "message": "SPEC-0024 — Build fehlgeschlagen, Exit-Code 1"}
{"type": "spec_implemented", "spec_id": "SPEC-0024", "message": "SPEC-0024 — implementiert"}
```

## Trigger-Mapping (SddRunService)

| Command | Exit-Code | `type` |
|---|---|---|
| `sdd orchestrate` | 0 | `orchestrate_done` |
| `sdd orchestrate` | ≠0 | `build_failed` |
| `sdd dev build` | 0 | `build_done` |
| `sdd dev build` | ≠0 | `build_failed` |
