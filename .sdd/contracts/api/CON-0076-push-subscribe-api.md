---
id: CON-0076
title: "push-subscribe-api"
type: api
format: openapi
spec: SPEC-0023
version: 0.1.0
status: draft
tests: [TST-0107]
---

# Contract: POST /api/push/subscribe

> **Spec:** SPEC-0023 · **Typ:** API · **Status:** draft

## Zweck

Registriert die Web-Push-Subscription eines Geräts im In-Memory PushStore.
Beim nächsten Broadcast-Ereignis (Orchestrate, Build) wird dieses Gerät
benachrichtigt.

## Garantien

| ID | Garantie |
|---|---|
| G-01 | Auth: `Authorization: Bearer <token>`. Fehlt / falsch → HTTP 401 |
| G-02 | Request-Body: Web-Push-Subscription-Objekt mit `endpoint` (URL) und `keys` (`p256dh`, `auth`) |
| G-03 | Gleicher `endpoint` → Subscription wird dedupliziert (kein Duplikat im PushStore) |
| G-04 | Fehlende VAPID-Keys in config.yaml → HTTP 503 mit `detail: "vapid_not_configured"` |
| G-05 | Erfolgreiche Registrierung → HTTP 201 `{"subscribed": true}` |
| G-06 | Subscription-Invalidierung: Bei HTTP 410 vom Push-Endpoint wird die Subscription automatisch aus dem Store entfernt |
| G-07 | PushStore ist In-Memory — Subscriptions gehen bei Server-Neustart verloren |

## Request-Body

```json
{
  "endpoint": "https://fcm.googleapis.com/fcm/send/xyz",
  "keys": {
    "p256dh": "BNcRdreALR...",
    "auth": "tBHItJI5svbpez7KI4CCXg=="
  }
}
```

## VAPID-Konfiguration

VAPID-Keys werden aus `config.yaml` unter dem Schlüssel `pwa.vapid` gelesen.
Pflichtfelder: `private_key` (PKCS8-PEM), `public_key` (Base64url), `claims_email`.
Fehlen diese Felder → HTTP 503. (CF-0023-007 resolved)

```yaml
pwa:
  vapid:
    private_key: "..."
    public_key: "..."
    claims_email: "mailto:user@example.com"
```

## Endpoint

```
POST /api/push/subscribe
Authorization: Bearer <token>
Content-Type: application/json
Response: 201 {"subscribed": true}
Response: 401 {"detail": "invalid_token"}
Response: 503 {"detail": "vapid_not_configured"}
```
