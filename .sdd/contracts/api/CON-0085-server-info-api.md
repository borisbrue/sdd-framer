---
id: CON-0085
title: "server-info API"
type: api
format: openapi
spec: SPEC-0025
version: 0.1.0
status: draft
tests: [TST-0095]
---

# Contract: server-info API

> **Spec:** SPEC-0025 · **Typ:** API · **Status:** draft

## Zweck

GET /api/server-info liefert Metadaten des laufenden Servers ohne Authentifizierung.
Dient der PWA zur Identifikation des Servers vor dem QR-Onboarding.

## Garantien

| ID | Garantie |
|---|---|
| G-01 | HTTP 200 ohne Authorization-Header |
| G-02 | Response: {name: string, externalUrl: string, tokenHash: string} |
| G-03 | tokenHash = SHA-256(token).hexdigest()[:8] — nie der rohe Token |
| G-04 | tokenHash ist leer wenn kein Token konfiguriert |
| G-05 | externalUrl ist leer wenn nicht konfiguriert |
| G-06 | name kommt aus project.name in config.yaml |

## Endpoint

```
GET /api/server-info
Response 200: { name, externalUrl, tokenHash }
```
