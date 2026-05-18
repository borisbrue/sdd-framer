---
id: CON-0093
title: "pwa-localstorage-schema"
type: data
format: json-schema
spec: SPEC-0024
version: 0.1.0
status: draft
tests: [TST-0103]
---

# Contract: PWA localStorage-Schema

> **Spec:** SPEC-0024 · **Typ:** Data Schema · **Status:** draft

## Zweck

Definiert das Schema für `sdd_config` im localStorage der PWA — die einzige
persistente Konfigurationsquelle des Remote-Clients.

## Schema

```typescript
interface SddConfig {
  baseUrl: string;       // Backend-URL, z.B. "http://rechner.ts.net:8000"
  token: string;         // Bearer-Token (64-char hex nach CON-0086)
  lastSpecId?: string;   // Letzte aktive Spec-ID für Tab-Routing
  pushSubId?: string;    // Push-Subscription-ID (optional, wenn Push aktiv)
}
```

**localStorage-Key:** `"sdd_config"` (JSON-String)

## Garantien

| ID | Garantie |
|---|---|
| G-01 | `baseUrl` ist immer eine valide URL (http:// oder https://) |
| G-02 | Wenn `sdd_config` in localStorage existiert, ist `token` niemals leer — ein leeres token-Feld ist kein gültiger Zustand |
| G-03 | `lastSpecId` entspricht dem Format `SPEC-XXXX` oder ist `undefined` |
| G-04 | Bei HTTP 401 wird der **gesamte** `sdd_config`-Key aus localStorage gelöscht (nicht nur das token-Feld). baseUrl geht dabei verloren — der Nutzer gibt sie im Setup-Screen erneut ein. (CF-0024-011, CF-0024-012, CF-0024-013 resolved) |
| G-05 | Nach erfolgreichem Setup-Flow enthält `sdd_config` mindestens `baseUrl` und `token` |
| G-06 | `pushSubId` speichert den vollständigen `subscription.endpoint`-URL der Web Push API — keine opake ID. (CF-0024-016 resolved) |

## Migration

Wenn `sdd_config` aus SPEC-0025 (`sdd_projects[]`) vorhanden ist:
- Das `sdd_config`-Key aus SPEC-0024 ist ein separates Objekt und kollidiert nicht
- `sdd_projects[]` (CON-0088) und `sdd_config` (CON-0093) koexistieren im localStorage

## Beispiel

```json
{
  "baseUrl": "http://rechner.tail12345.ts.net:8000",
  "token": "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
  "lastSpecId": "SPEC-0024",
  "pushSubId": "https://fcm.googleapis.com/fcm/send/xyz"
}
```
