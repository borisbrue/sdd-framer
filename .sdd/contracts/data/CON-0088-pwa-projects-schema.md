---
id: CON-0088
title: "pwa-projects-schema"
type: data
format: json-schema
spec: SPEC-0025
version: 0.1.0
status: draft
tests: [TST-0098]
---

# Contract: PWA Projects Schema

> **Spec:** SPEC-0025 · **Typ:** Data Schema · **Status:** draft

## Zweck

Definiert das Schema für `sdd_projects[]` im localStorage der PWA sowie
die Kompatibilitätsanforderungen an die Server-API.

## Schema (localStorage)

```typescript
interface Project {
  id: string;        // UUID v4, client-generiert
  name: string;      // aus QR-Payload / manuelle Eingabe
  baseUrl: string;   // externe URL des Servers
  token: string;     // 64-char hex (nach Token-Rotation)
  addedAt: string;   // ISO 8601 timestamp
}
```

## Garantien

| ID | Garantie |
|---|---|
| G-01 | token ist immer 64 Hex-Zeichen (Ergebnis von rotate-token) |
| G-02 | sdd_projects[] wird atomar geschrieben (kein Halbzustand) |
| G-03 | sdd Version 1 im QR-Payload ist Pflicht |
| G-04 | url in qr-payload wird zu baseUrl im Project |
| G-05 | name in qr-payload wird zu name im Project |
| G-06 | server-info tokenHash (8 Zeichen) ist niemals der rohe Token |
| G-07 | Jede Token-Rotation erzeugt einen einzigartigen neuen Token |
