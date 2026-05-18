---
id: SPEC-0024
project: PRJ-0001
title: Dedicated PWA Shell — Remote SDD Client für iOS & Android
status: approved
owner: Boris
created: 2026-05-17
updated: '2026-05-17'
version: 0.1.0
priority: high
tags:
- pwa
- mobile
- chat
- dashboard
- push-notifications
- tailscale
- remote
depends_on:
- SPEC-0023
contracts:
- CON-0090
- CON-0091
- CON-0092
- CON-0093
- CON-0094
tests:
- TST-0100
- TST-0101
- TST-0102
- TST-0103
- TST-0104
adrs: []
---
# Dedicated PWA Shell — Remote SDD Client für iOS & Android

> **Status:** draft · **Owner:** Boris · **Version:** 0.1.0

## 1. Kontext & Motivation

SDD-Entwicklung ist jetzt via SPEC-0023 remote steuerbar — die Backend-API
(`/ws/chat`, `/api/sdd/run`, `/api/push/subscribe`) existiert vollständig.
Was fehlt ist ein dedizierter mobiler Client, der unabhängig vom bestehenden
Web-UI ist und auf den Entwicklungsrechner via Tailscale/VPN zugreift.

**Das Problem:**
- Das bestehende SDD Web-UI (`web/ui`) ist an localhost gebunden — kein Remote-Zugriff
- Keine installierbare App auf dem Handy
- Keine Push-Notifications auf iOS/Android
- Kein durchgängiger Remote-Workflow: Spec schreiben → Flow beobachten → Rückfragen beantworten

**Die Lösung:** Eine eigenständige PWA (`web/pwa/`) mit konfigurierbarer Backend-URL
(z. B. `http://rechner.tail12345.ts.net:8000`), Bearer-Token-Setup, Chat-Interface,
Command-Panel, Pipeline-Dashboard und Push-Notification-Integration. Die PWA wird
vom gleichen FastAPI-Backend unter `/pwa/` ausgeliefert — kein zweiter Server nötig.

## 2. Zielsetzung

**Primärziel:** Vollständiger SDD-Remote-Workflow vom Handy: Spec beschreiben →
Flow triggern → Rückfragen beantworten → Ergebnisse überwachen — alles ohne SSH
oder Bildschirm am Entwicklungsrechner.

### Erfolgskriterien (messbar)

- PWA ist auf iOS 16+ (Safari) und Android 10+ (Chrome) via "Zum Homescreen hinzufügen" installierbar
- Setup-Screen beim ersten Start: Backend-URL + Bearer-Token eingeben, in localStorage persistieren
- Chat mit Claude: Nachricht senden → Intent erkannt → SDD-Command ausgeführt → Antwort
- Pipeline-Dashboard zeigt alle Specs mit Gate-Phase + Status live (Polling / SSE)
- Command-Panel: `sdd orchestrate`, `sdd start`, `sdd dev build` per Button auslösbar, Output live sichtbar
- Log-Viewer: `/ws/logs/{spec_id}` mit ANSI-Farben und Auto-Scroll
- Push-Notification bei Orchestrate-Abschluss: Tippen öffnet die PWA direkt am richtigen Tab
- Verbindungsaufbau via Tailscale/VPN funktioniert ohne weitere Konfiguration
- Multi-User-ready: Token-Eingabe pro Gerät, Backend unterstützt mehrere Sessions

### Nicht-Ziele

- Kein Code-Editor in der PWA — nur Steuerung und Beobachtung
- Kein Cloud-Hosting / Multi-Tenant — läuft lokal, Zugang via Tailscale/VPN
- Kein App-Store-Release — PWA-Installation reicht
- Kein eigenes Auth-System — Bearer-Token aus SPEC-0023 wird direkt genutzt
- Kein Offline-Modus mit vollem Feature-Set — nur grundlegendes Caching via Service Worker

## 3. Architektur & Design

### 3.1 Systemübersicht

```
Handy / Remote-Browser (iOS/Android)
  └── PWA (web/pwa/ — Vite + React + vite-plugin-pwa)
        ├── Setup Screen      → Backend-URL + Token → localStorage
        ├── Chat Tab          ←→ WebSocket /ws/chat  (SPEC-0023 CON-0074)
        ├── Command Tab       →  POST /api/sdd/run   (SPEC-0023 CON-0075)
        ├── Dashboard Tab     ←  GET /api/specs       (Polling 10s)
        ├── Log Tab           ←→ WebSocket /ws/logs/{spec_id} (SPEC-0022)
        └── Push Handler      ←  Service Worker → Notification-Tap → Tab-Routing

FastAPI Backend (Entwicklungsrechner, via Tailscale erreichbar)
  └── GET /pwa/{path}  → web/pwa/dist/ (statische PWA-Dateien)
  └── [alle SPEC-0023-Endpoints unverändert]
```

### 3.2 Design Patterns

**Facade Pattern** (`ApiClient`): Kapselt alle Backend-Kommunikation. Liest URL + Token
aus `config.ts` und setzt automatisch `Authorization: Bearer <token>` auf alle Requests.
UI-Komponenten kennen keine URLs — nur ApiClient-Methoden.
[Refactoring Guru – Facade](https://refactoring.guru/design-patterns/facade)

**Observer Pattern** (`ConnectionStore`): Zentraler reaktiver Zustand
(`connected | disconnected | setup_required`) — alle Tabs abonnieren ihn. Bei HTTP 401
→ `setup_required` → automatische Weiterleitung zum Setup-Screen.
[Refactoring Guru – Observer](https://refactoring.guru/design-patterns/observer)

**Strategy Pattern** (`NotificationStrategy`): Wählt automatisch zwischen
`WebPushStrategy` (Hintergrund) und `InAppStrategy` (Vordergrund-Toast). Kein
doppeltes Notifizieren.
[Refactoring Guru – Strategy](https://refactoring.guru/design-patterns/strategy)

### 3.3 Setup-Flow & Token-Persistenz

```
Erster Start:
  → SetupScreen: Backend-URL + Bearer-Token eingeben
  → ApiClient.validate() → GET /api/specs (Auth-Check)
  → Erfolg: speichern in localStorage, weiter zu Dashboard
  → Fehler: Fehlermeldung, erneut versuchen

Folgestarts:
  → Config aus localStorage laden
  → Stille Validierung im Hintergrund
  → Bei 401: zurück zu SetupScreen (Token abgelaufen / geändert)
```

## 4. Funktionale Anforderungen

- **FR-01** Die PWA hat ein Web App Manifest mit `display: standalone`, Icons (192×192, 512×512 maskable) und `theme_color`. Installierbar auf iOS 16+ (Safari) und Android 10+ (Chrome).
- **FR-02** Setup-Screen beim ersten Start: Backend-URL + Bearer-Token. Validierung via GET /api/specs (HTTP 200 erwartet) vor dem Speichern in localStorage.
- **FR-03** Chat-Tab öffnet WebSocket zu `/ws/chat`. Streaming-Tokens als `{"delta": "..."}`, Command-Output als Code-Block eingebettet.
- **FR-04** Command-Tab: Buttons für `orchestrate` (mit Spec-Auswahl), `start`, `dev build`, `dev up`, `dev down`. Output via POST `/api/sdd/run` + SSE live.
- **FR-05** Dashboard-Tab pollt GET `/api/specs` alle 10 Sekunden. Zeigt id, title, status, pipeline_phase, priority. Tippen → Log-Tab.
- **FR-06** Log-Tab: `/ws/logs/{spec_id}` mit ANSI-Farbenrendering und Auto-Scroll. Spec-Auswahl per Dropdown.
- **FR-07** Service Worker Push-Handler: Systembenachrichtigung bei eingehender Push. Tap → PWA öffnet richtigen Tab.
- **FR-08** ApiClient setzt `Authorization: Bearer <token>` auf alle Requests. Bei HTTP 401 → Setup-Screen, Token aus localStorage löschen.
- **FR-09** Multi-User-ready: jedes Gerät hat eigenen Token in localStorage. Backend (SPEC-0023) unterstützt mehrere parallele Sessions.
- **FR-10** FastAPI serviert `web/pwa/dist/` unter `/pwa/`. `vite.config.ts` setzt `base: '/pwa/'`.

## 5. User Stories

| ID | Als … | möchte ich … | damit … |
|---|---|---|---|
| US-01 | Entwickler | vom Handy aus eine Spec beschreiben | Claude sie anlegt ohne dass ich am Rechner bin |
| US-02 | Entwickler | den Gate-Status aller Specs sehen | ich weiß wo welches Feature steht |
| US-03 | Entwickler | `sdd orchestrate` per Knopfdruck starten | ich den Lauf remote anstoße |
| US-04 | Entwickler | eine Push-Notification bei Orchestrate-Abschluss | ich nicht aktiv warten muss |
| US-05 | Entwickler | Container-Logs live sehen | ich den Build verfolge ohne SSH |
| US-06 | Entwickler | Backend-URL und Token ändern | ich mit einem anderen Rechner verbinde |

## 6. Contracts

| Contract-ID | Typ | Was wird garantiert? |
|---|---|---|
| CON-0090 | api (openapi) | ApiClient — alle Backend-Calls mit Auth-Header + Error-Handling |
| CON-0091 | behavior (gherkin) | Setup-Flow — URL + Token validieren vor Speichern |
| CON-0092 | behavior (gherkin) | Service Worker Push-Handler — Notification + Tab-Navigation |
| CON-0093 | data (json-schema) | localStorage-Schema — Backend-URL, Token, letzte aktive Spec |
| CON-0094 | performance (slo-yaml) | Dashboard-Polling — Antwort < 200 ms, Polling-Interval 10 s |

## 7. Tests

| Test-ID | Level | Was prüft der Test? |
|---|---|---|
| TST-0100 | unit | ApiClient — Auth-Header gesetzt, 401 → Setup-Redirect |
| TST-0101 | contract | Setup-Flow — GET /api/specs Format-Validierung |
| TST-0102 | contract | Service Worker Push-Handler — Notification-Format |
| TST-0103 | unit | localStorage-Schema — sdd_config Felder vorhanden |
| TST-0104 | performance | Dashboard-Polling GET /api/specs p95 < 200ms |

## 8. Implementierungsreihenfolge

- **Phase A:** Projekt-Setup — Vite + React + vite-plugin-pwa, manifest.json, Icons
- **Phase B:** Config + ApiClient — localStorage-Schema, Facade, Token-Header, 401-Handler
- **Phase C:** Setup-Screen — URL + Token eingeben, validate(), speichern, weiterleiten
- **Phase D:** Dashboard-Tab — GET /api/specs Polling, Spec-Karten
- **Phase E:** Chat-Tab — WebSocket /ws/chat, Streaming-Render, Command-Output-Blöcke
- **Phase F:** Command-Tab — Buttons → /api/sdd/run, SSE-Output, Spec-Auswahl
- **Phase G:** Log-Tab — /ws/logs/{spec_id}, ANSI-Farben, Auto-Scroll
- **Phase H:** Push-Notifications — Service Worker, Notification-Tap → Tab-Navigation
- **Phase I:** FastAPI-Integration — /pwa/ StaticFiles, base-URL in vite.config.ts

## 9. Offene Fragen

- Icons: Generisches Dev-Icon für v0.1 → ✓ Entschieden
- ANSI-Farben: `ansi-to-html` npm-Paket → ✓ Entschieden
- Offline-Fallback: letzter Dashboard-Snapshot aus Cache + Reconnect-Banner
- Push-Permission iOS: Permission-Request im Setup-Flow nach Token-Validierung

## 10. Änderungshistorie

| Datum | Version | Autor | Änderung |
|---|---|---|---|
| 2026-05-17 | 0.1.0 | Boris | Initiale Erstellung |
