---
id: TST-0172
project: ''
title: Hub-Health-Endpunkt erkennt Online- und Offline-Zustand
level: integration
spec: SPEC-0040
contract: CON-0149
status: planned
framework: ''
artifact: tests/unit/test_tst_0172.py
tags: []
---
## Was wird geprüft?

Dieser Test verifiziert, dass der Health-Endpunkt des Hubs korrekt auf zwei Zustände reagiert:

- **Online-Fall:** Der Hub ist erreichbar → der Endpunkt antwortet mit HTTP 200 und einem definierten JSON-Body, der den Verbindungsstatus eindeutig als `online` ausweist.
- **Offline-Fall:** Die Hub-Verbindung ist unterbrochen → der Endpunkt liefert ein klar interpretierbares Fehlersignal (HTTP 503 oder Netzwerkfehler), das den Übergang der PWA in den Offline-Modus auslöst.

Der Test deckt FR-08 (Verbindungsstatus überwachen) und FR-06 (Offline-Anzeige) ab.

---

## Vorbedingungen

- Eine Testinstanz des Hubs (oder ein Mock-Server, der das Hub-API-Verhalten nachbildet) ist gestartet und unter einer konfigurierten Basis-URL erreichbar.
- Der Health-Endpunkt (`GET /health` o. Ä. gemäß CON-0149) ist im Hub aktiviert.
- Die PWA-Schicht, die den Endpunkt aufruft, ist isoliert testbar (z. B. als Service-Klasse oder HTTP-Client-Modul).
- Netzwerk-Interception oder ein kontrollierbarer Mock-Adapter (z. B. `msw`, `nock`, `httpretty`) ist verfügbar, um den Verbindungsabbruch zu simulieren.
- Keine echten Hub-Prozesse oder Produktionsdaten sind involviert; die Testumgebung ist vollständig isoliert.

---

## Ablauf

### Szenario 1 — Hub online

1. Mock-Server antwortet auf `GET /health` mit HTTP 200 und dem vertragskonformen JSON-Body (z. B. `{ "status": "ok", "hub": "reachable" }`).
2. Der PWA-Health-Service ruft den Endpunkt auf.
3. Die Antwort wird ausgewertet: Statuscode und Body werden gegen das im Contract definierte Schema validiert.
4. Der interne Verbindungszustand des Services wird abgefragt.

### Szenario 2 — Hub offline (Verbindungsabbruch)

1. Mock-Server wird so konfiguriert, dass er auf `GET /health` entweder:
   - HTTP 503 zurückgibt (Service Unavailable), oder
   - die Verbindung verweigert / das Request-Timeout überschreitet (Netzwerkfehler).
2. Der PWA-Health-Service ruft den Endpunkt auf.
3. Die Fehlerantwort wird ausgewertet.
4. Es wird geprüft, ob der Service den Offline-Modus aktiviert (d. h. ein entsprechendes Event emittiert oder ein State-Flag setzt).

### Szenario 3 — Wiederherstellung (optional, aber empfohlen)

1. Nach Szenario 2 wird der Mock-Server wieder in den Online-Zustand versetzt.
2. Beim nächsten Health-Check erkennt der Service den Hub als wieder erreichbar.
3. Der Verbindungszustand wechselt zurück auf online.

---

## Erwartetes Ergebnis

| Szenario | HTTP-Status | Body | Verbindungszustand im Service |
|---|---|---|---|
| Hub online | `200` | Schema-konform gemäß CON-0149 | `online` |
| Hub offline (503) | `503` | Beliebig (kein Schema-Zwang) | `offline` |
| Hub offline (Netzwerkfehler) | kein Status (Exception) | — | `offline` |
| Wiederherstellung | `200` | Schema-konform | `online` |

Der Statuswechsel muss deterministisch und ohne manuelle Intervention ausgelöst werden — der Service darf den Zustand nicht im `online`-Status belassen, wenn der Endpunkt nicht erreichbar ist.

---

## Negativfälle / Edge Cases

- **HTTP 200 mit leerem oder malformiertem Body:** Der Service soll dies als Fehler behandeln und in den Offline-Modus wechseln, da der Contract einen validen Body vorschreibt.
- **HTTP 200 mit falschem `status`-Wert** (z. B. `"status": "degraded"`): Verhalten gemäß CON-0149 spezifizieren; sofern der Contract nur `"ok"` als gültigen Wert zulässt, muss auch dies als Offline-Signal gewertet werden.
- **Sehr hohe Latenz (Timeout):** Antwortet der Hub nach Ablauf eines definierten Timeouts (z. B. 3 s) nicht, wird dies wie ein Verbindungsabbruch behandelt.
- **Intermittierende Verbindung:** Wechsel online → offline → online innerhalb kurzer Zeit darf nicht zu einem Race Condition im Zustandsautomaten führen; der zuletzt empfangene Zustand ist maßgeblich.
- **Erster Aufruf schlägt fehl:** Auch ohne vorherigen Online-Zustand muss der Service sofort auf `offline` schalten und darf keinen `undefined`-Initialzustand offen lassen.

---

## Verknüpfung mit dem Contract

Dieser Test validiert **CON-0149** vollständig auf Integrationsebene:

- Das OpenAPI-Schema aus CON-0149 definiert den erwarteten Response-Body für HTTP 200; der Test führt eine Schema-Validierung gegen dieses Artefakt durch (nicht gegen eine hardkodierte Erwartung).
- Die im Contract beschriebene Semantik des Fehlersignals (HTTP 503 oder Verbindungsfehler → Offline-Modus) wird durch Szenario 2 direkt abgedeckt.
- Änderungen am Contract-Artefakt (z. B. neue Pflichtfelder im Body) müssen diesen Test ohne zusätzliche Anpassung regressionssicher scheitern lassen.

---

## Hinweise zur Implementierung

**Framework:** Pytest (Backend-Integration) oder Vitest/Jest mit `msw` (Frontend-Service-Integration) — abhängig davon, ob der Health-Service in Python oder TypeScript implementiert ist.

**Mock-Strategie:**
- Frontend (TypeScript): `msw` (Mock Service Worker) im Node-Modus für Unit-/Integrationstests ohne Browser; ermöglicht präzise Steuerung von Status-Codes und Timeouts.
- Backend (Python): `responses` oder `httpretty` für synchrone HTTP-Clients; `aioresponses` für `aiohttp`/`httpx`.

**Schema-Validierung:** Das OpenAPI-Artefakt aus CON-0149 direkt einlesen und mit `jsonschema` (Python) oder `ajv` (JS) gegen die tatsächliche Antwort prüfen — keine duplizierten Inline-Schemas im Testcode.

**Timeout-Simulation:** Mock-Server-Antwort mit einem `delay` konfigurieren, der den konfigurierten Client-Timeout (empfohlen: 3 s) überschreitet, um Netzwerkstillstand zu simulieren, ohne OS-Netzwerkrechte zu benötigen.

**Assertions auf Zustandsänderungen:** Den internen Verbindungsstatus über das öffentliche Interface des Services abfragen (Event, Observable, Property) — nicht über private Implementierungsdetails, um Refactoring-Stabilität zu gewährleisten.