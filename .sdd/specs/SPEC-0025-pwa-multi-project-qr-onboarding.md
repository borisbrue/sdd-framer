---
id: SPEC-0025
project: PRJ-0001
title: 'PWA Multi-Projekt, QR-Onboarding & Token-Rotation'
status: implemented
owner: Boris
created: 2026-05-17
updated: '2026-05-17'
version: 0.1.0
priority: high
tags:
- pwa
- qr-code
- auth
- token-rotation
- multi-project
depends_on:
- SPEC-0022
contracts:
- CON-0085
- CON-0086
- CON-0087
- CON-0088
- CON-0089
tests:
- TST-0095
- TST-0096
- TST-0097
- TST-0098
- TST-0099
adrs: []
---
# PWA Multi-Projekt, QR-Onboarding & Token-Rotation

> **Status:** implemented · **Owner:** Boris · **Version:** 0.1.0

## 1. Kontext & Motivation

Die SDD PWA soll mehrere Projekte (auf verschiedenen Hosts) verwalten können.
Das Onboarding eines neuen Projekts erfolgt durch Scannen eines QR-Codes, der
im Web UI angezeigt wird. Nach dem Scan rotiert die PWA den Token, damit er
nach der Einrichtung nicht mehr aus dem QR-Code extrahiert werden kann.

## 2. Zielsetzung

### Erfolgskriterien
- GET /api/server-info liefert Name, External-URL und Token-Hash ohne Auth
- POST /api/auth/rotate-token rotiert den Token atomar und invalidiert den alten
- GET /api/auth/qr-payload liefert den vollständigen QR-Inhalt (nur lokal)
- PWA zeigt alle konfigurierten Projekte und ermöglicht Wechsel
- Token-Rotation erfolgt sofort nach QR-Scan (keine Halbzustände)

### Nicht-Ziele
- Kein serverseitiges User-Management
- Keine Zwei-Faktor-Authentifizierung
- Keine verschlüsselte Übertragung (Voraussetzung: HTTPS im Deployment)

## 3. Architektur & Design Patterns

**Command Pattern** (`rotate_token`): Klar abgegrenzter Befehl mit verify →
generate → persist → invalidate. Ermöglicht atomare Fehlbehandlung.
[Refactoring Guru – Command](https://refactoring.guru/design-patterns/command)

**Composite Pattern** (`ProjectRegistry`): Einheitliche Verwaltung beliebig
vieler Projekte in `sdd_projects[]` im localStorage.
[Refactoring Guru – Composite](https://refactoring.guru/design-patterns/composite)

**Template Method Pattern** (`QrOnboardingFlow`): Der Onboarding-Ablauf
(scan → validate → rotateToken → saveProject → navigate) ist als invariante
Schablone implementiert; die Schritte sind einzeln austauschbar.
[Refactoring Guru – Template Method](https://refactoring.guru/design-patterns/template-method)

## 4. Funktionale Anforderungen

- FR-01: GET /api/server-info – kein Auth, gibt name/externalUrl/tokenHash zurück
- FR-02: tokenHash = SHA-256(token)[:8] – niemals der rohe Token
- FR-03: POST /api/auth/rotate-token – Bearer-Auth, atomic config write
- FR-04: Alter Token wird sofort in In-Memory-Blacklist eingetragen
- FR-05: GET /api/auth/qr-payload – gibt vollständigen QR-Inhalt zurück (404 wenn nicht konfiguriert)
- FR-06: CLI-Flags --external-url und --allowed-origins konfigurieren CORS
- FR-07: PWA ProjectRegistry verwaltet sdd_projects[] im localStorage
- FR-08: PWA QrOnboardingFlow führt Token-Rotation durch bevor Projekt gespeichert wird
- FR-09: PWA unterstützt manuellen Projekteintrag als Fallback (ohne Kamera)
- FR-10: CORS-Origins aus SDD_ALLOWED_ORIGINS Umgebungsvariable

## 5. Contracts

- CON-0085: GET /api/server-info – öffentlich, kein Auth
- CON-0086: POST /api/auth/rotate-token – Bearer-Auth, atomic rotation
- CON-0087: QR-Onboarding-Flow (server-side: /auth/qr-payload)
- CON-0088: sdd_projects[] localStorage-Schema
- CON-0089: SLO – server-info p95 < 100ms, rotate-token p95 < 500ms

## 6. Tests

- TST-0095: CON-0085 server-info endpoint (6 Tests)
- TST-0096: CON-0086 rotate-token endpoint (6 Tests)
- TST-0097: CON-0087 qr-payload endpoint (5 Tests)
- TST-0098: CON-0088 schema-compatibility (7 Tests)
- TST-0099: CON-0089 SLO-Performance (2 Tests)

## 7. Implementierungsreihenfolge

1. `web/api/sdd_context.py` – blacklist, external_url, reload_config
2. `web/api/routes/auth.py` – server-info, qr-payload, rotate-token
3. `web/api/main.py` – Router einbinden, CLI-Flags
4. `web/ui/src/components/ServerInfoPanel.tsx` – QR-Overlay
5. `web/pwa/` – ProjectRegistry, QrOnboardingFlow, QrScanner, Screens

## 8. Änderungshistorie

| Version | Datum | Änderung |
|---|---|---|
| 0.1.0 | 2026-05-17 | Initiale Erstellung |
