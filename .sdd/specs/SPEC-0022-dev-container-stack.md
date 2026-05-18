---
id: SPEC-0022
title: 'Dev-Container-Stack: Image-Building, Registry, Compose und Live-Logging'
status: in-progress
owner: Boris
created: 2026-05-17
updated: '2026-05-17'
version: 0.1.0
priority: high
tags:
- docker
- podman
- compose
- registry
- live-logging
- frontend
- ci
depends_on:
- SPEC-0021
contracts:
- CON-0069
- CON-0070
- CON-0071
- CON-0072
- CON-0073
tests:
- TST-0079
- TST-0080
- TST-0081
- TST-0082
- TST-0083
adrs: []
started_at: '2026-05-17T06:50:08Z'
---
# Dev-Container-Stack: Image-Building, Registry, Compose und Live-Logging

> **Status:** draft · **Owner:** Boris · **Version:** 0.1.0

## 1. Kontext & Motivation

SPEC-0021 definiert `sdd dev start/exec/close/pr` und setzt voraus, dass ein
lauffähiges Docker-Image (`sdd-dev:latest`) bereits existiert. Diese Voraussetzung
ist nicht erfüllt ohne eine definierte Lösung für:

- **Image-Building:** Wie und wo entsteht `sdd-dev:latest`?
- **Registry:** Wie wird das Image verteilt (lokal, remote, CI)?
- **Compose:** Wie werden Multi-Service-Stacks (Dev-Container + Datenbank, Broker etc.)
  verwaltet?
- **Runtime-Auswahl:** Docker ist nicht überall verfügbar — Podman ist eine
  gleichwertige Alternative (rootless, daemonless), besonders in CI und auf
  Linux-Systemen ohne Docker-Daemon.
- **Live-Logging:** Entwickler und DevOps brauchen Sichtbarkeit in laufende
  Container-Prozesse ohne in die Shell wechseln zu müssen. Das SDD Web UI
  soll Container-Logs pro Spec in Echtzeit darstellen.

**Das Problem:** Ohne diese Spec ist `sdd dev start` nur nutzbar wenn ein
Entwickler manuell ein Image gebaut und konfiguriert hat. Es gibt keinen
reproduzierbaren, dokumentierten Weg von 0 zu einem laufenden Dev-Container.

**Die Lösung:** Neue `sdd dev build/push/up/down`-Befehle + konfigurierbare
Runtime-Abstraktion + WebSocket-basiertes Live-Logging im SDD Web UI.

---

## 2. Zielsetzung

**Primärziel:**
Entwickler, CI und DevOps können den gesamten Container-Stack über die SDD-CLI
und `.sdd/config.yaml` konfigurieren und starten. Arbeitsfortschritte sind
im SDD Web UI als Live-Log pro Spec sichtbar.

**Erfolgskriterien (messbar):**

- [ ] `sdd dev build` baut das konfigurierten Image aus dem definierten Dockerfile
- [ ] Runtime ist in `.sdd/config.yaml` auf `docker` oder `podman` umschaltbar —
      alle `sdd dev`-Befehle aus SPEC-0021 funktionieren mit beiden Runtimes
- [ ] `sdd dev push` schiebt das Image in die konfigurierte Registry (lokal oder remote)
- [ ] `sdd dev up SPEC-XXXX` startet einen Multi-Service-Stack via Compose
      (dev-Container + optionale Services)
- [ ] `sdd dev down SPEC-XXXX` stoppt den gesamten Compose-Stack
- [ ] Das SDD Web UI zeigt Container-Logs für eine laufende Spec in Echtzeit
      (WebSocket oder SSE, < 1 s Verzögerung)
- [ ] Alle Einstellungen (Runtime, Image, Registry, Compose-Datei) sind in
      `.sdd/config.yaml` unter dem `docker:`-Namespace konfigurierbar
- [ ] CI kann denselben Stack ohne manuelle Eingriffe bauen und starten

**Nicht-Ziele:**
_(keine expliziten Nicht-Ziele definiert)_

---

## 3. Architektur & Design

### 3.1 Konfigurationsschema (`.sdd/config.yaml`)

```yaml
docker:
  runtime: docker          # docker | podman
  image: sdd-dev:latest    # Ziel-Image-Name
  dockerfile: .sdd/Dockerfile   # Pfad zum Dockerfile
  registry:
    url: ""                # leer = kein Push; z.B. "registry.example.com/sdd"
    auth_env: ""           # Env-Var mit Registry-Credentials (z.B. REGISTRY_TOKEN)
  compose_file: ".sdd/docker-compose.yml"   # leer = kein Compose
  log_stream:
    enabled: true
    max_lines: 500         # Maximale Log-Zeilen im UI-Buffer
```

### 3.2 CLI-Befehle (Erweiterung von `sdd dev`)

```
sdd dev build              → docker/podman build -t <image> -f <dockerfile> .
sdd dev push               → docker/podman push <registry>/<image>
sdd dev up   SPEC-XXXX     → docker/podman compose -f <compose_file> up -d
sdd dev down SPEC-XXXX     → docker/podman compose -f <compose_file> down
```

`sdd dev start` (SPEC-0021) wird intern auf `sdd dev up` delegiert wenn
`compose_file` konfiguriert ist — sonst wie bisher (`docker run`).

### 3.3 Design Patterns

#### Strategy Pattern (Behavioral)
**Anwendung:** `ContainerRuntime` ist ein austauschbares Interface:
- `DockerRuntime`: delegiert an `docker`-CLI
- `PodmanRuntime`: delegiert an `podman`-CLI (API-kompatibel)

`DevContainerManager` (SPEC-0021) erhält eine `ContainerRuntime`-Instanz
statt direkter `docker`-Aufrufe. Runtime wird aus `docker.runtime` in
`config.yaml` aufgelöst.

**Begründung:** Ohne Strategy würden `docker`-Aufrufe im Code hardgecodet.
Neue Runtimes (z.B. nerdctl, containerd) erfordern keinen Code-Change am Manager
(OCP). Runtime-spezifische Flags (z.B. Podman `--userns=keep-id`) sind in der
jeweiligen Strategy gekapselt.

**Refactoring Guru:** https://refactoring.guru/design-patterns/strategy

#### Observer Pattern (Behavioral)
**Anwendung:** Der Log-Streamer beobachtet laufende Container-Prozesse und
benachrichtigt alle registrierten Frontend-Clients (WebSocket-Connections)
bei neuen Log-Zeilen. Ein `LogEventBus` hält die aktiven Subscriptions:

```
Container-Prozess
  → LogStreamer (liest docker/podman logs --follow)
    → LogEventBus.publish(spec_id, line)
      → [WebSocket-Client-1, WebSocket-Client-2, …].send(line)
```

**Begründung:** Das Frontend kann sich zur Laufzeit an- und abmelden ohne
dass der Streamer davon weiß (lose Kopplung). Mehrere Browser-Tabs können
denselben Log-Stream empfangen (Multicast).

**Refactoring Guru:** https://refactoring.guru/design-patterns/observer

### 3.4 Live-Logging Architektur

```
sdd dev up / start
  └─ LogStreamer.attach(spec_id, container_name)
       └─ Thread: docker logs --follow sdd-dev-spec-xxxx
            └─ LogEventBus.publish(spec_id, line)
                 └─ WebSocket /ws/logs/{spec_id}
                      └─ SDD Web UI: LogPanel Komponente
```

**Frontend:** Neuer `LogPanel`-Tab im Spec-Detail-View.
Zeigt max. `log_stream.max_lines` Zeilen, Auto-Scroll, ANSI-Farben.

---

## 4. Funktionale Anforderungen

**FR-01** `sdd dev build` baut das Image aus `docker.dockerfile` mit dem Tag
`docker.image`. Runtime gemäß `docker.runtime` (`docker` oder `podman`).

**FR-02** Alle `sdd dev`-Befehle (SPEC-0021: start, exec, close, pr) und neue
Befehle (build, push, up, down) delegieren Runtime-Aufrufe an eine
`ContainerRuntime`-Instanz — kein direkter `docker`-Aufruf im Code.

**FR-03** `sdd dev push` schiebt `docker.image` in `docker.registry.url`.
Credentials werden aus der Env-Var `docker.registry.auth_env` gelesen.
Wenn `registry.url` leer ist: Warnung + Abbruch.

**FR-04** Wenn `docker.compose_file` konfiguriert ist, delegiert `sdd dev start`
(SPEC-0021 FR-01) intern an `sdd dev up`. Ohne `compose_file`: bisheriges
Verhalten (`docker run` direkt).

**FR-05** `sdd dev up SPEC-XXXX` startet den Compose-Stack mit
`docker compose -f <compose_file> up -d`. Container-Name-Konvention
aus SPEC-0021 bleibt erhalten.

**FR-06** `sdd dev down SPEC-XXXX` stoppt den Compose-Stack mit
`docker compose -f <compose_file> down`.

**FR-07** Nach `sdd dev up/start` startet `LogStreamer.attach()` automatisch
wenn `log_stream.enabled: true`. Log-Stream läuft bis `sdd dev down/close`.

**FR-08** Das SDD Web UI exponiert `/ws/logs/{spec_id}` als WebSocket-Endpoint.
Bei Verbindungsaufbau werden die letzten `log_stream.max_lines` Zeilen
aus dem Buffer gesendet, danach Live-Zeilen.

**FR-09** Der `LogPanel` im Frontend zeigt Logs mit ANSI-Farbunterstützung
und Auto-Scroll. Maximale Buffer-Größe: `log_stream.max_lines`.

**FR-10** CI-Kompatibilität: `sdd dev build && sdd dev push` ist ohne
interaktive Eingaben ausführbar (alle Parameter aus `config.yaml` + Env-Vars).

---

## 5. User Stories

| ID | Als … | möchte ich … | damit … |
|---|---|---|---|
| US-01 | Entwickler | mit `sdd dev build` ein reproduzierbares Image bauen | ich nicht manuell `docker build` mit korrekten Flags aufrufen muss |
| US-02 | Entwickler | zwischen Docker und Podman wechseln können | ich die Runtime wähle, die auf meinem System verfügbar ist |
| US-03 | Entwickler | Container-Logs live im Web UI sehen | ich nicht in die Shell wechseln muss um Fortschritt zu verfolgen |
| US-04 | DevOps | `sdd dev push` für CI konfigurieren | Images automatisch in die Registry gebaut werden |
| US-05 | Entwickler | mit `sdd dev up/down` einen Multi-Service-Stack starten | ich Abhängigkeiten (DB, Broker) automatisch mitlaufen lasse |
| US-06 | CI-System | `sdd dev build && sdd dev up` ohne Eingaben ausführen | der CI-Lauf vollautomatisch läuft |

---

## 6. Contracts

_(werden in eigenen CON-Dokumenten ausgearbeitet)_

| Contract-ID | Typ | Was wird garantiert? |
|---|---|---|
| — | behavior | `sdd dev build/push/up/down` Lifecycle + Runtime-Auswahl |
| — | behavior | LogStreamer: attach/detach, Buffer-Größe, WebSocket-Format |
| — | api | `/ws/logs/{spec_id}` WebSocket-Endpoint-Schema |
| — | data | `.sdd/config.yaml` `docker:`-Namespace Schema |
| — | performance | Log-Latenz < 1 s (Container → UI) |

---

## 7. Tests

_(werden in eigenen TST-Dokumenten ausgearbeitet)_

| Test-ID | Level | Was prüft der Test? |
|---|---|---|
| — | unit | `DockerRuntime` und `PodmanRuntime` delegieren korrekte CLI-Befehle |
| — | unit | `LogEventBus` multicast zu N Subscribers |
| — | contract | `sdd dev build` mit Docker + mit Podman |
| — | contract | WebSocket `/ws/logs/{spec_id}` liefert Zeilen in < 1 s |
| — | acceptance | Vollständiger Stack: build → up → live-logs im UI → down |

---

## 8. Implementierungsreihenfolge

```
Phase A: ContainerRuntime-Interface + DockerRuntime + PodmanRuntime
  └─ DevContainerManager (SPEC-0021) auf Runtime-Interface umstellen

Phase B: sdd dev build / push
  └─ CLI-Befehle + Config-Auflösung

Phase C: sdd dev up / down (Compose)
  └─ sdd dev start delegiert an up wenn compose_file konfiguriert

Phase D: LogStreamer + LogEventBus
  └─ Thread-basiertes docker logs --follow
  └─ Buffer-Management (max_lines)

Phase E: WebSocket-Endpoint /ws/logs/{spec_id}
  └─ Integration in bestehenden SDD Web UI Server (SPEC-0003)

Phase F: Frontend LogPanel
  └─ Neuer Tab im Spec-Detail-View

Phase G: Contracts + Tests
```

---

## 9. Offene Fragen

- [ ] Welche Services soll das Default-`docker-compose.yml` enthalten?
      → Vorschlag: nur dev-Container; optionale Services per Override-File
- [ ] Soll `sdd dev build` beim ersten `sdd dev start` automatisch triggern
      wenn kein Image vorhanden ist?
      → Vorschlag: Ja, mit explizitem Hinweis an den Nutzer
- [ ] ANSI-Farben im LogPanel: eigene Implementierung oder Bibliothek?
      → Vorschlag: `xterm.js` (bereits in vielen Dev-UIs verwendet)
- [ ] Soll der Log-Buffer persistent sein (`.sdd/logs/`) oder nur in-memory?
      → Vorschlag: in-memory für v0.1, persistente Logs in v0.2

---

## 10. Änderungshistorie

| Datum | Version | Autor | Änderung |
|---|---|---|---|
| 2026-05-17 | 0.1.0 | Boris | Initiale Erstellung |
