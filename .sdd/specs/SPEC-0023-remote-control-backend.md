---
id: SPEC-0023
project: PRJ-0001
title: Remote Control Backend — Chat, SDD-Run & Push-Notifications
status: in-progress
owner: Boris
created: 2026-05-18
updated: '2026-05-18'
version: 0.1.0
priority: high
tags:
- remote
- websocket
- chat
- claude
- push-notifications
- sse
- tailscale
depends_on:
- SPEC-0021
- SPEC-0022
contracts:
- CON-0074
- CON-0075
- CON-0076
- CON-0077
- CON-0078
tests:
- TST-0105
- TST-0106
- TST-0107
- TST-0108
- TST-0109
adrs: []
started_at: '2026-05-18T07:55:45Z'
---
# Remote Control Backend — Chat, SDD-Run & Push-Notifications

> **Status:** draft · **Owner:** Boris · **Version:** 0.1.0

## 1. Kontext & Motivation

Das bestehende SDD-Backend (FastAPI) ist nur für localhost zugänglich. Ein
mobiler Client (SPEC-0024 PWA) braucht drei neue Fähigkeiten:

1. **Chat mit Claude** — WebSocket `/ws/chat`: der Nutzer schreibt eine Nachricht,
   Claude erkennt die Absicht, führt den passenden SDD-Command aus und antwortet
   mit Streaming-Tokens + eingebettetem Command-Output.

2. **Beliebige SDD-Commands remote auslösen** — POST `/api/sdd/run`: sendet den
   Output als Server-Sent Events live zurück; bei Abschluss wird optional eine
   Push-Notification gesendet.

3. **Push-Notifications** — POST `/api/push/subscribe`: registriert die
   Web-Push-Subscription eines Geräts; der Server broadcastet beim Abschluss
   eines Orchestrate- oder Build-Laufs.

## 2. Zielsetzung

**Primärziel:** Vollständige Remote-Steuerung via Handy ohne SSH — identische
Fähigkeiten wie die lokale CLI, aber über eine authentifizierte API.

### Erfolgskriterien

- `/ws/chat` nimmt Nachrichten entgegen, schickt `{"delta": "..."}` Streaming-Tokens zurück und führt erkannte SDD-Intents automatisch aus
- `/api/sdd/run` führt jeden validen `sdd`-Command aus und streamt Output als SSE
- `/api/push/subscribe` speichert Subscriptions und invalidiert sie bei Fehler automatisch
- Nach jedem `sdd orchestrate` oder `sdd dev build` erhalten alle registrierten Geräte eine Push-Notification
- Authentifizierung via Bearer-Token (identisch mit SPEC-0025 CON-0086) auf allen Endpoints

### Nicht-Ziele

- Kein eigenes LLM-Hosting — Claude API via Anthropic SDK
- Kein Multi-User-Berechtigungssystem — ein Token, ein Server
- Keine persistente Chat-History über Neustarts hinaus (In-Memory)
- Kein Rate-Limiting in v0.1

## 3. Architektur & Design

### 3.1 Systemübersicht

```
PWA / Remote-Client
  ├── WS /ws/chat          → ChatService (Intent Erkennung + Command Dispatch)
  ├── POST /api/sdd/run    → SddRunService (Subprocess + SSE-Stream)
  └── POST /api/push/subscribe → PushStore (Subscription-Registry)

ChatService
  ├── Claude API (Anthropic SDK, stream=True)
  ├── IntentParser — erkennt: orchestrate, start, dev-build, dev-up, dev-down, status
  └── CommandDispatcher → SddRunService.run(cmd, args)

SddRunService
  ├── subprocess.Popen(["sdd", cmd, ...], stdout=PIPE, stderr=STDOUT)
  ├── SSE-Stream: {"type": "line", "data": "..."}
  └── bei Abschluss: PushStore.broadcast({"type": "orchestrate_done", "spec_id": ...})

PushStore
  ├── In-Memory-Liste: [PushSubscription, ...]
  └── broadcast(payload) → pywebpush für jede Subscription
```

### 3.2 Design Patterns

**Chain of Responsibility** (`IntentParser`): Jeder Intent-Handler prüft die
Nachricht und entscheidet, ob er sie verarbeitet oder weitergibt. Neue Intents
werden als Handler hinzugefügt — ohne bestehende zu ändern (OCP).
[Refactoring Guru – Chain of Responsibility](https://refactoring.guru/design-patterns/chain-of-responsibility)

**Observer Pattern** (`PushStore`): Alle registrierten Geräte sind Subscriber;
bei einem relevanten Event (`orchestrate_done`, `build_failed`) werden alle
benachrichtigt. Geräte können sich abmelden (Subscription-Invalidierung bei
410 Gone).
[Refactoring Guru – Observer](https://refactoring.guru/design-patterns/observer)

**Facade Pattern** (`SddRunService`): Kapselt `subprocess.Popen` + SSE-Formatting
+ PushStore-Integration hinter einer einfachen `run(cmd, args)` → AsyncGenerator-Schnittstelle.
[Refactoring Guru – Facade](https://refactoring.guru/design-patterns/facade)

### 3.3 Auth-Middleware

Alle drei Endpoints prüfen `Authorization: Bearer <token>` gegen den Token aus
`config.yaml → pwa.auth.token` (identisch mit CON-0086). Bei fehlendem oder
falschem Token → HTTP 401.

### 3.4 Datenhaltung

- **PushStore:** In-Memory (verliert Subscriptions bei Server-Neustart). Geräte
  re-subscriben beim nächsten PWA-Start.
- **Chat-History:** In-Memory-Liste von `{"role": ..., "content": ...}` pro Session.
  Pro WebSocket-Verbindung eine Session. Kein Cross-Session-State.

## 4. Funktionale Anforderungen

- **FR-01** `GET /ws/chat` — WebSocket, Bearer-Auth im ersten Frame oder HTTP-Header. Empfängt `{"text": "..."}`, sendet Streaming-Tokens als `{"delta": "..."}`, Command-Output als `{"type": "command_output", "line": "..."}`, Abschluss als `{"type": "done"}`.
- **FR-02** IntentParser erkennt Intents: `orchestrate <SPEC-ID>`, `start <SPEC-ID>`, `dev build`, `dev up`, `dev down`, `status`. Nicht erkannte Nachrichten → direkt an Claude ohne Command-Ausführung.
- **FR-03** `POST /api/sdd/run` — Bearer-Auth, Body `{"cmd": "orchestrate", "args": ["SPEC-0024"]}`, Response als SSE-Stream. Jede Zeile als `data: {"type": "line", "data": "..."}`, Abschluss als `data: {"type": "done", "exit_code": 0}`.
- **FR-04** `POST /api/push/subscribe` — Bearer-Auth, Body ist ein Web-Push-Subscription-Objekt (`endpoint`, `keys`). Server speichert in PushStore. Doppelte Subscriptions (gleicher `endpoint`) werden dedupliziert.
- **FR-05** Nach `sdd orchestrate` oder `sdd dev build/up/down` broadcastet SddRunService via PushStore. Payload: `{"type": "orchestrate_done" | "build_done" | "build_failed", "spec_id": "...", "message": "..."}`.
- **FR-06** Subscription-Invalidierung: Bei HTTP 410 Gone von einem Push-Endpoint entfernt PushStore die Subscription automatisch.
- **FR-07** Chat-Kontext: Claude erhält immer die letzten 20 Nachrichten der Session als Context. System-Prompt definiert Claude als SDD-Assistent.
- **FR-08** Bearer-Auth-Middleware prüft alle drei Endpoints. Bei 401 → WebSocket wird mit Code 4001 geschlossen, HTTP-Endpoints geben 401 zurück.
- **FR-09** VAPID-Keys für Push werden beim Serverstart aus `config.yaml → pwa.vapid` geladen; fehlen sie, ist Push deaktiviert (FR-04 gibt 503 zurück).

## 5. User Stories

| ID | Als … | möchte ich … | damit … |
|---|---|---|---|
| US-01 | Entwickler | "Starte Orchestrate für SPEC-0024" schreiben | Claude den Lauf auslöst |
| US-02 | Entwickler | `sdd orchestrate` per API auslösen | ich nicht SSH brauche |
| US-03 | Entwickler | eine Push-Notification bei Abschluss | ich nicht aktiv warten muss |
| US-04 | Entwickler | den Command-Output live sehen | ich den Fortschritt verfolge |
| US-05 | Entwickler | mehrere Geräte registrieren | jedes Gerät die Notification bekommt |

## 6. Contracts

| Contract-ID | Typ | Was wird garantiert? |
|---|---|---|
| CON-0074 | api (openapi) | WebSocket /ws/chat — Auth, Streaming-Format, Intent-Dispatch |
| CON-0075 | api (openapi) | POST /api/sdd/run — SSE-Format, Exit-Code, Push-Trigger |
| CON-0076 | api (openapi) | POST /api/push/subscribe — Subscription-Format, Dedup, 503 ohne VAPID |
| CON-0077 | data (json-schema) | Push-Notification-Payload — type, spec_id, message |
| CON-0078 | performance (slo-yaml) | /ws/chat first-token < 200ms (LLM gemockt), /api/sdd/run first-line < 1s |

## 7. Tests

| Test-ID | Level | Was prüft der Test? |
|---|---|---|
| TST-0105 | contract | /ws/chat Auth + Streaming-Format |
| TST-0106 | contract | /api/sdd/run SSE-Format + Exit-Code |
| TST-0107 | contract | /api/push/subscribe Dedup + 503 ohne VAPID |
| TST-0108 | unit | IntentParser — alle 6 Intents erkannt, Unbekannte passieren |
| TST-0109 | performance | first-token < 200ms (LLM gemockt), first-line < 1s (CF-0023-017 resolved) |

## 8. Implementierungsreihenfolge

- **Phase A:** Bearer-Auth-Middleware für alle drei Endpoints
- **Phase B:** SddRunService — subprocess + SSE-Generator
- **Phase C:** PushStore — In-Memory, broadcast, Subscription-Invalidierung
- **Phase D:** /api/sdd/run Endpoint
- **Phase E:** /api/push/subscribe Endpoint
- **Phase F:** IntentParser — Chain of Responsibility, 6 Handler
- **Phase G:** ChatService — Claude Streaming + IntentParser-Integration
- **Phase H:** /ws/chat WebSocket-Endpoint
- **Phase I:** main.py — Router einbinden, VAPID-Config-Check

## 9. Offene Fragen

- VAPID-Key-Generierung: einmalig via `pywebpush` beim Setup oder manuell? → Vorschlag: `sdd init` ergänzen
- Chat-History-Länge: 20 Nachrichten für GPT-4-Kontext ausreichend? → Vorschlag: konfigurierbar via config.yaml
- Anthropic-Model: claude-sonnet-4-6 als Default? → Ja, laut Umgebungsvariable

## 10. Änderungshistorie

| Datum | Version | Autor | Änderung |
|---|---|---|---|
| 2026-05-18 | 0.1.0 | Boris | Initiale Erstellung aus SPEC-0024-Kontext |
