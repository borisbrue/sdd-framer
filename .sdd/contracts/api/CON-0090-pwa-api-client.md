---
id: CON-0090
title: "pwa-api-client"
type: api
format: openapi
spec: SPEC-0024
version: 0.1.0
status: draft
tests: [TST-0100]
---

# Contract: PWA ApiClient (Facade)

> **Spec:** SPEC-0024 · **Typ:** API · **Status:** draft

## Zweck

Der `ApiClient` kapselt alle Backend-Kommunikation der PWA (Facade Pattern).
Er liest Backend-URL und Token aus `localStorage` und setzt automatisch
`Authorization: Bearer <token>` auf jeden Request.

## Garantien

| ID | Garantie |
|---|---|
| G-01 | Jeder HTTP-Request enthält `Authorization: Bearer <token>` aus localStorage |
| G-02 | Bei HTTP 401 wird der gesamte `sdd_config`-Key aus localStorage gelöscht und ConnectionStore auf `setup_required` gesetzt (CF-0024-013 resolved) |
| G-03 | `connectChat()` öffnet WebSocket zu `<baseUrl>/ws/chat` |
| G-04 | `runCommand(cmd, args)` sendet POST zu `<baseUrl>/api/sdd/run` |
| G-05 | `getSpecs()` sendet GET zu `<baseUrl>/api/specs` und gibt Array zurück |
| G-06 | `connectLogs(spec_id)` öffnet WebSocket zu `<baseUrl>/ws/logs/<spec_id>` |
| G-07 | `subscribePush(subscription)` sendet POST zu `<baseUrl>/api/push/subscribe` |
| G-08 | Netzwerkfehler setzen ConnectionStore auf `disconnected` |

## Schnittstelle

```typescript
interface ApiClient {
  connectChat(): WebSocket;
  runCommand(cmd: string, args: string[]): EventSource;
  getSpecs(): Promise<Spec[]>;
  connectLogs(specId: string): WebSocket;
  subscribePush(sub: PushSubscription): Promise<void>;
  validate(): Promise<boolean>;  // GET /api/specs → 200 = ok
}
```

## Fehlerbehandlung

- `401 Unauthorized` → gesamten `sdd_config`-Key löschen, `connectionStore.set("setup_required")` (CF-0024-013 resolved)
- Netzwerkfehler / Timeout → `connectionStore.set("disconnected")` — kein eigener Retry, Polling-Intervall aus CON-0094 ist maßgeblich (CF-0024-017 resolved)
- WebSocket `onclose` → `connectionStore.set("disconnected")`
