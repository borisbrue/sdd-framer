---
id: CON-0087
title: "qr-onboarding-flow"
type: api
format: openapi
spec: SPEC-0025
version: 0.1.0
status: draft
tests: [TST-0097]
---

# Contract: QR-Onboarding-Flow (server-side)

> **Spec:** SPEC-0025 · **Typ:** API · **Status:** draft

## Zweck

GET /api/auth/qr-payload liefert den vollständigen QR-Code-Inhalt — ausschließlich
für das lokal laufende Web UI. Externe Clients erhalten keinen Zugriff (CORS).

## Garantien

| ID | Garantie |
|---|---|
| G-01 | Response: {sdd: 1, name: string, url: string, token: string} |
| G-02 | token ist der vollständige Token (64 Hex-Zeichen), nicht der Hash |
| G-03 | HTTP 404 wenn kein Token konfiguriert (detail: "no_token_configured") |
| G-04 | HTTP 404 wenn keine External-URL konfiguriert (detail: "no_external_url_configured") |
| G-05 | name stammt aus project.name in config.yaml |

## Endpoint

```
GET /api/auth/qr-payload
Response 200: { sdd: 1, name, url, token }
Response 404: { detail: "no_token_configured" | "no_external_url_configured" }
```

## Onboarding-Ablauf (Template Method Pattern)

1. scan — PWA scannt QR-Code mit jsQR (iOS-kompatibel)
2. validate — JSON-Schema: sdd, name, url, token
3. rotateToken — POST /api/auth/rotate-token mit altem Token
4. saveProject — Neues Projekt in sdd_projects[] speichern
5. navigate — ProjectSwitcher anzeigen
