---
id: SPEC-0032
title: Mobile Agentic Workflow – Vollständige SDD-Steuerung via PWA & Push
type: feature
status: implemented
owner: Boris
created: 2026-05-30
updated: '2026-05-30'
version: 0.2.0
priority: medium
tags: []
depends_on:
- SPEC-0003
- SPEC-0005
- SPEC-0007
- SPEC-0015
- SPEC-0016
- SPEC-0023
- SPEC-0024
- SPEC-0025
- SPEC-0028
contracts:
- CON-0114
- CON-0115
- CON-0116
tests:
- TST-0133
- TST-0134
- TST-0135
adrs: []
started_at: '2026-05-30T19:58:03Z'
---
# Mobile Agentic Workflow – Vollständige SDD-Steuerung via PWA & Push

> **Status:** draft · **Owner:** Boris · **Version:** 0.1.0

## 1. Kontext & Motivation

SDD ist heute terminal-gebunden: Specs anlegen, reviewen, implementieren —
alles erfordert eine aktive Claude-Code-Session am Rechner. Unterwegs ist das
nicht nutzbar. SPEC-0023/0024/0025 haben eine PWA-Shell und ein Remote-Backend
eingeführt, SPEC-0028 hat Gate-Buttons im Web UI. Der fehlende Baustein ist der
**geführte Conversational Flow**: Der Entwickler soll vom Smartphone aus denselben
Workflow ausführen können, den er heute im Terminal-Chat hat — `/sdd-new spec`,
`/sdd-review`, `/sdd-implement`, `/sdd-hotfix` — ohne jemals den Rechner anfassen
zu müssen. Der Server übernimmt die autonome Ausführung, das Smartphone bekommt
Push-Notifications wenn etwas abgeschlossen ist oder eine Entscheidung nötig ist.

## 2. Zielsetzung

**Primärziel:**
Ein Entwickler kann auf dem Smartphone einen neuen Spec starten, die Fragen in
der PWA beantworten, den Implementierungsjob auf dem Server auslösen und eine
Push-Notification erhalten wenn der PR bereit ist — ohne den Rechner zu berühren.

**Erfolgskriterien (messbar):**

- [ ] `/sdd-new spec` ist als geführter Chat-Flow in der PWA aufrufbar: Fragen
      erscheinen nacheinander, Antworten werden gesendet, Spec wird auf dem Server
      angelegt
- [ ] `/sdd-review SPEC-XXXX` nutzt die bestehende SPEC-0016-Async-Analyse-Infrastruktur;
      SOLID-Check (SPEC-0015), Pattern-Suggest und Regression-Check erscheinen als
      strukturierte Antwort in der PWA
- [ ] `/sdd-implement SPEC-XXXX` delegiert an den bestehenden SPEC-0007-Orchestrator
      (`POST /api/orchestrate`); der Entwickler bekommt eine Push-Notification wenn
      der PR fertig ist oder eine Entscheidung nötig ist
- [ ] `/sdd-hotfix` ist als geführter Flow in der PWA aufrufbar
- [ ] `sdd status` ist als Übersichtsscreen in der PWA jederzeit abrufbar
- [ ] Tunnel-Zugang (Cloudflare Tunnel / Tailscale) ist in `.sdd/config.yaml`
      konfigurierbar; die PWA verbindet sich automatisch über die konfigurierte URL

**Nicht-Ziele (explizit):**

- Kein LLM auf dem Gerät — alle KI-Calls laufen auf dem Server
- Kein Offline-Modus
- Keine Multi-User-Unterstützung
- Kein eigenes Tunnel-Protokoll (Cloudflare/Tailscale/ngrok als externe Tools)
- Kein Editieren von Dateien direkt in der PWA (Dateisystem bleibt Server-seitig)

## 3. Architektur & Design Patterns

### Pattern 1 — Facade
**Zweck:** Ein einheitlicher `/api/agent/flow` Endpunkt kapselt alle Skill-Flows
(`new-spec`, `review`, `implement`, `hotfix`). Die PWA kommuniziert nur mit
diesem einen Endpunkt — sie muss nicht wissen welche internen Befehle dahinter
stehen.

**Abgrenzung zu bestehenden Routen (SPEC-0003):** Die `AgentFlowFacade`
*delegiert* an existierende Endpunkte aus SPEC-0003 und SPEC-0007. Sie ersetzt
keine bestehenden Routen und depreciert keine vorhandene API. Bestehende
Web-UI-Endpunkte bleiben unverändert erreichbar.

**Refactoring Guru:** https://refactoring.guru/design-patterns/facade

```
PWA → POST /api/agent/flow
        └── AgentFlowFacade
              ├── NewSpecFlow    → delegiert an SPEC-0005: PUT /api/docs/{id}/analyze
              ├── ReviewFlow     → delegiert an SPEC-0016: POST /api/docs/{id}/analyze/start
              ├── ImplementFlow  → delegiert an SPEC-0007: POST /api/orchestrate
              └── HotfixFlow     → neu (kein bestehender Endpunkt)
```

### Pattern 2 — Command + Async Queue
**Zweck:** Jeder Flow ist ein Command-Objekt mit `execute()` (async, Server-seitig)
und `status()`. Langläufige Commands verwenden die **bereits bestehende
Job-Infrastruktur**:

- **ReviewFlow** nutzt `AnalysisJobStore` aus SPEC-0016 (`POST /api/docs/{id}/analyze/start`,
  `GET /api/docs/{id}/analyze/status/{job_id}`) — kein eigener Job-Store.
- **ImplementFlow** delegiert an `POST /api/orchestrate` (SPEC-0007) und pollt
  `GET /api/pipeline/{run_id}` — kein eigener Orchestrator.
- **Push-Notifications** verwenden den bestehenden `NotificationContext` + Toast-Mechanismus
  aus SPEC-0016 (FR-18–FR-20) und SPEC-0023 — keine zweite Notification-Infrastruktur.

**Refactoring Guru:** https://refactoring.guru/design-patterns/command

```
AgentFlowCommand (ABC)
  ├── execute() → job_id (aus SPEC-0016 oder SPEC-0007 JobStore)
  ├── status()  → idle | running | awaiting_input | done | failed
  └── push()    → Push-Notification via bestehendem SPEC-0016/SPEC-0023 System
```

### Pattern 3 — State Machine (Conversational Flow)
**Zweck:** Geführte Flows wie `/sdd-new spec` bestehen aus mehreren Schritten
mit Nutzer-Input. Ein State-Machine-Modell hält den aktuellen Schritt, die
bisherigen Antworten und den nächsten erwarteten Input — servergesteuert, PWA
zeigt nur den aktuellen State an.

**Refactoring Guru:** https://refactoring.guru/design-patterns/state

```
FlowSession
  ├── state: step_1 | step_2 | … | done | awaiting_confirm
  ├── answers: {}
  └── next_prompt: str
```

## 4. Funktionale Anforderungen

- **FR-01:** `POST /api/agent/flow/start` — startet einen neuen Flow-Session
  (`type`: `new-spec` | `review` | `implement` | `hotfix`). Gibt `session_id`
  + ersten Prompt zurück.
  `new-spec`-Sessions bauen auf der bestehenden KI-Analyse-Session-Infrastruktur aus
  SPEC-0005 (§3.3, Session-Tracking) auf — kein eigener Gesprächs-State für
  bereits abgedeckte Flows.
- **FR-02:** `POST /api/agent/flow/{session_id}/reply` — sendet eine Nutzer-Antwort
  an den laufenden Flow. Gibt nächsten Prompt oder `{done: true, job_id}` zurück.
- **FR-03:** Langläufige Jobs nutzen die **bestehende** Job-Infrastruktur ohne eigenen
  Job-Store:
  - `review`-Jobs: `AnalysisJobStore` aus SPEC-0016; Status-Polling via
    `GET /api/docs/{doc_id}/analyze/status/{job_id}`
  - `implement`-Jobs: `PipelineRunState` aus SPEC-0007; Status-Polling via
    `GET /api/pipeline/{run_id}`
  Der `AgentFlowFacade` mappt die `session_id` auf die interne `job_id`/`run_id`
  des jeweiligen Subsystems.
- **FR-04:** Push-Notifications nach Job-Abschluss verwenden das **bestehende**
  `NotificationContext` + Toast-System aus SPEC-0016 (FR-18–FR-20) als In-App-Kanal
  und SPEC-0023 als PWA-Push-Kanal — keine zweite Notification-Infrastruktur.
- **FR-05:** Bei Entscheidungspunkten (z.B. "Pattern annehmen?", "Weiter trotz
  Warning?") pausiert der Job und sendet eine Push-Notification mit Aktionsbuttons
  (`ja` / `nein`). Der Entwickler antwortet über die PWA, der Job läuft weiter.
- **FR-06:** `GET /api/agent/flow/{session_id}` — gibt den aktuellen Flow-State
  zurück (für PWA-Reconnect nach App-Neustart).
- **FR-07:** `GET /api/status` — bereits implementiert in SPEC-0007 (§4.1). SPEC-0032
  erweitert den bestehenden Endpunkt um ein optionales `active_flows`-Feld
  (`{ session_id, type, state }`-Array), das laufende Agentic-Flow-Sessions auflistet.
  Kein neuer Endpunkt; kein Ersetzen des bestehenden Schemas.
- **FR-08:** `.sdd/config.yaml` erhält eine neue Sektion `tunnel` mit der
  öffentlichen URL der SDD-Instanz:
  ```yaml
  tunnel:
    url: https://sdd.example.com   # Cloudflare/Tailscale/ngrok URL
  ```
  Die PWA liest diese URL beim ersten QR-Onboarding (SPEC-0025) ein.
- **FR-09:** `/sdd-hotfix`-Flow in der PWA: Bug beschreiben → Server legt
  HF-Record an → Server implementiert Fix → PR-Commit → Push-Notification.

## 5. User Stories

| ID    | Als ...    | möchte ich ...                                                      | um ...                                                        |
| ----- | ---------- | ------------------------------------------------------------------- | ------------------------------------------------------------- |
| US-01 | Entwickler | vom Smartphone aus `/sdd-new spec` starten                          | unterwegs neue Features in Auftrag geben                      |
| US-02 | Entwickler | eine Push-Notification erhalten wenn der PR fertig ist              | ohne aktiv warten oder den Rechner prüfen zu müssen           |
| US-03 | Entwickler | bei Entscheidungspunkten (Pattern, Warning) per Push benachrichtigt werden | den Flow nicht unbeaufsichtigt stecken zu lassen       |
| US-04 | Entwickler | `sdd status` als Übersicht in der PWA sehen                         | jederzeit den Projektstand im Blick zu haben                  |
| US-05 | Entwickler | einen Hotfix von unterwegs einleiten                                | dringende Bugs sofort beheben ohne Laptop aufklappen zu müssen|

## 6. Contracts

*(werden in `/sdd-new contract` ergänzt)*

## 7. Tests

*(werden in `/sdd-new test` ergänzt)*

## 8. Implementierungsreihenfolge

**Vorbedingung:** SPEC-0003, SPEC-0005, SPEC-0007, SPEC-0016, SPEC-0023,
SPEC-0024, SPEC-0025, SPEC-0028 müssen den Status `implemented` haben.
SPEC-0015 (SOLID/Pattern Gate) ist für `ReviewFlow` vorausgesetzt.

1. `AgentFlowFacade` + `FlowSession` State Machine (FR-01, FR-02, FR-06)
2. `NewSpecFlow` — wraps SPEC-0005-Session-Tracking für `/sdd-new spec` als PWA-Flow
3. `ReviewFlow` — wraps SPEC-0016-JobStore für `/sdd-review` als asynchronen Job
4. Push-Notification-Bridge: mappt SPEC-0016/SPEC-0023-Events auf PWA-Flow-Sessions (FR-04, FR-05)
5. `ImplementFlow` — delegiert an SPEC-0007 `POST /api/orchestrate`
6. `HotfixFlow` — `/sdd-hotfix` als geführter Flow (FR-09, kein bestehender Endpunkt)
7. `GET /api/status` erweitern um `active_flows`-Feld (FR-07, Erweiterung von SPEC-0007)
8. Tunnel-Konfiguration in `config.yaml` + PWA-Anpassung (FR-08)

## 9. Offene Fragen

- [ ] Welcher Tunnel-Dienst wird empfohlen? Cloudflare Tunnel (kostenlos, stabil)
      oder Tailscale (einfacheres Setup)?
- [ ] Sollen Flow-Sessions persistent sein (Server-Neustart überlebt)?
      Oder reicht In-Memory mit Push-Notification als Recovery?
- [ ] Wie lange darf ein `implement`-Job maximal laufen bevor ein Timeout greift?
- [ ] Sollen Entscheidungs-Notifications auch per E-Mail/ntfy.sh kommen als
      Fallback wenn die PWA nicht offen ist?

## 10. Änderungshistorie

| Datum      | Version | Autor | Änderung            |
| ---------- | ------- | ----- | ------------------- |
| 2026-05-30 | 0.1.0   | Boris | Initiale Erstellung |
| 2026-05-30 | 0.2.0   | Boris | Regression-Konflikte aufgelöst: depends_on um SPEC-0003/0005/0007/0015/0016 ergänzt; AgentFlowFacade als Delegation-Layer über bestehenden Endpunkten spezifiziert; FR-03/04/07 explizit auf existierende Job-/Notification-/Status-Infrastruktur referenziert |
