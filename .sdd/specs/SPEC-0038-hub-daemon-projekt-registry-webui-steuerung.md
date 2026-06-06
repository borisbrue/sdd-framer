---
id: SPEC-0038
title: Hub-Daemon mit Projekt-Registry und WebUI-Steuerung
type: feature
status: in-progress
owner: borisbrue
created: 2026-06-06
updated: '2026-06-06'
version: 0.3.0
priority: medium
tags:
- hub
- daemon
- systemd
- webui
- project-registry
- remote-control
depends_on:
- SPEC-0003
- SPEC-0007
- SPEC-0016
- SPEC-0023
- SPEC-0024
- SPEC-0025
contracts:
- CON-0130
- CON-0131
- CON-0132
- CON-0133
- CON-0134
- CON-0135
- CON-0136
- CON-0137
- CON-0138
- CON-0139
tests:
- TST-0152
- TST-0153
- TST-0154
- TST-0155
- TST-0156
- TST-0157
- TST-0158
- TST-0159
- TST-0160
- TST-0161
adrs: []
started_at: '2026-06-06T10:08:42Z'
---
# Hub-Daemon mit Projekt-Registry und WebUI-Steuerung

## 1. Kontext & Motivation

Heute muss jeder Projektserver manuell in einem Terminal gestartet werden.
Bei Remote-Arbeit von einem anderen Gerät bedeutet das: SSH-Session öffnen,
Terminal navigieren, Kommando ausführen — und der Rechner muss erreichbar und
die Session aktiv sein. Bricht die Verbindung ab, läuft der Server u. U. weiter
ohne Kontrolle, oder er stirbt mit der Session.

SPEC-0003 (sdd-web-ui) und SPEC-0023 (remote-control-backend) legen die Basis
für eine Web-basierte Steuerung einzelner Projekte. SPEC-0024/0025 definieren
die PWA-Shell und Multi-Projekt-Onboarding. Was fehlt: eine zentrale Instanz,
die dauerhaft läuft, alle registrierten Projekte kennt und deren Lebenszyklen
verwaltet — unabhängig davon ob gerade jemand eingeloggt ist.

SPEC-0038 schließt diese Lücke: Der Hub läuft als systemd-User-Service,
startet automatisch beim Boot, führt eine Projekt-Registry, und stellt eine
WebUI bereit über die alle Projekte per Klick gestartet und gestoppt werden
können — ohne Terminal, ohne SSH-Session.

## 2. Zielsetzung

**Primärziel:**
Boris öffnet von einem beliebigen Gerät aus die Hub-WebUI, sieht alle
registrierten Projekte mit aktuellem Status (running / stopped), und kann
einen Projektserver per Klick starten oder stoppen — ohne Terminal.

**Erfolgskriterien (messbar):**
- [ ] Hub startet automatisch beim System-Boot als systemd-User-Service und
      ist nach Reboot ohne manuellen Eingriff erreichbar
- [ ] Alle registrierten Projekte erscheinen in der WebUI mit Status-Badge
      (running / stopped) und werden innerhalb von 2 s nach Statuswechsel
      live aktualisiert
- [ ] Ein Projektserver lässt sich per Klick aus der WebUI starten und stoppen;
      der tatsächliche Prozess-Start ist innerhalb von 5 s sichtbar

**Nicht-Ziele (explizit):**
- Keine Benutzer-Authentifizierung oder Mehrbenutzer-Support (nur Boris,
  nur im lokalen Netz / VPN)
- Kein automatisches Starten von Projektservern beim Hub-Boot (nur auf
  explizite Nutzeranfrage)
- Kein Deployment auf Remote-Server — der Hub verwaltet nur lokal laufende
  Prozesse auf dem selben Host
- Kein Reverse-Proxy-Setup oder TLS-Termination (out of scope)
- Kein Monitoring / Alerting bei Prozessabsturz (nur Status-Anzeige)

## 3. Architektur & Design Patterns

### Pattern 1 — Registry
> [Refactoring Guru – keine direkte Seite; verwandt mit Service Locator](https://refactoring.guru/design-patterns/catalog)

`ProjectRegistry` ist die zentrale Datenstruktur: eine YAML-persistierte Liste
aller bekannten Projekte mit Metadaten (Name, Pfad, Start-Kommando, Port,
Status). Projekte registrieren sich einmalig via `sdd hub register`; danach
verwaltet der Hub ihren Lebenszyklus autonom.

**Begründung:** Zentrale Registry vermeidet, dass jedes Projekt seinen eigenen
State pflegen muss. Der Hub ist Single Source of Truth für Prozess-Status —
kein Polling einzelner Projekte nötig.

```python
class ProjectEntry(BaseModel):
    id: str
    name: str
    path: Path
    start_cmd: list[str]
    port: int
    status: Literal["running", "stopped", "error"]
    pid: int | None = None
    last_started: datetime | None = None

class ProjectRegistry:
    def register(self, entry: ProjectEntry) -> None: ...
    def get_all(self) -> list[ProjectEntry]: ...
    def update_status(self, id: str, status: str, pid: int | None) -> None: ...
```

### Pattern 2 — Command
> [Refactoring Guru – Command](https://refactoring.guru/design-patterns/command)

Start- und Stop-Aktionen aus der WebUI werden als `ProjectCommand`-Objekte
modelliert. `StartProjectCommand` und `StopProjectCommand` kapseln die
Prozess-Logik und werden vom `ProcessManager` ausgeführt.

**Begründung:** Entkoppelt HTTP-Handler von Prozess-Management. Commands sind
eigenständig testbar und können ohne WebUI-Kontext ausgeführt werden
(z. B. per CLI oder in Tests). Kein direktes `subprocess.Popen` in
Route-Handlern.

```python
class ProjectCommand(Protocol):
    project_id: str
    def execute(self, manager: ProcessManager) -> None: ...

class StartProjectCommand:
    def execute(self, manager: ProcessManager) -> None:
        manager.start(self.project_id)

class StopProjectCommand:
    def execute(self, manager: ProcessManager) -> None:
        manager.stop(self.project_id)
```

### Pattern 3 — Observer (Server-Sent Events)
> [Refactoring Guru – Observer](https://refactoring.guru/design-patterns/observer)

`ProcessManager` publiziert Status-Events (`started`, `stopped`, `error`) in
einen `StatusEventBus`. Der SSE-Endpoint `/projects/stream` ist Subscriber und
streamt Events an alle verbundenen WebUI-Clients. Die WebUI aktualisiert
Status-Badges ohne Page-Reload.

**Begründung:** SSE ist unidirektional (Server→Client) und ausreichend für
Status-Updates. Kein WebSocket-Overhead. Nutzt dieselbe SSE-Infrastruktur wie
SPEC-0007 — kein zweiter Transport-Layer.

### Komponentenübersicht

```
systemd user-service
    └── Hub FastAPI App (uvicorn)
            ├── ProjectRegistry (YAML: ~/.config/sdd/hub-registry.yaml)
            ├── ProcessManager (subprocess + PID-tracking)
            │       └── publiziert StatusEvents → StatusEventBus
            ├── GET  /hub/projects              → ProjectRegistry.get_all()
            ├── POST /hub/projects/{id}/start   → StartProjectCommand
            ├── POST /hub/projects/{id}/stop    → StopProjectCommand
            ├── GET  /hub/projects/stream       → SSE ← StatusEventBus
            └── WebUI /hub/projects             → Status-Liste + Start/Stop-Buttons
```

## 4. Funktionale Anforderungen

- **FR-01:** Hub läuft als systemd-User-Service (`~/.config/systemd/user/sdd-hub.service`),
  startet automatisch beim Login (`systemctl --user enable sdd-hub`),
  überlebt Reboots ohne manuelle Intervention. Standard-Port: 8080,
  konfigurierbar via `~/.config/sdd/hub.yaml` (Schlüssel: `hub.port`).

- **FR-02:** `sdd hub register --name <name> --path <pfad> --cmd <kommando> --port <port>`
  trägt ein Projekt in die Registry ein (`~/.config/sdd/hub-registry.yaml`).
  Duplicate-Check via `id` (abgeleitet aus `name`). Bestehende Einträge
  werden mit `--force` überschrieben.

- **FR-03:** `GET /hub/projects` gibt alle Registry-Einträge zurück als JSON-Array
  mit Feldern: `id`, `name`, `path`, `port`, `status`, `pid`, `last_started`.
  Status wird live aus `ProcessManager` ermittelt (nicht nur aus YAML).

- **FR-04:** WebUI-Seite `/hub/projects` zeigt alle Projekte als Karten mit:
  Name, Port, Status-Badge (grün=running, grau=stopped, rot=error),
  Start- und Stop-Button (je nach aktuellem Status aktiv/inaktiv).

- **FR-05:** `POST /hub/projects/{id}/start` startet den Prozess via `subprocess.Popen`
  mit dem registrierten `start_cmd` im registrierten `path`. PID wird in
  Registry gespeichert. Response: `{"status": "starting", "pid": <pid>}`.
  Wenn bereits running: HTTP 409.

- **FR-06:** `POST /hub/projects/{id}/stop` sendet SIGTERM an den Prozess. Nach
  10 s Timeout SIGKILL. PID wird aus Registry entfernt, Status auf `stopped`
  gesetzt. Wenn bereits stopped: HTTP 409.

- **FR-07:** `GET /hub/projects/stream` ist ein SSE-Endpoint der `StatusEvent`-Objekte
  streamt (`{id, status, pid, timestamp}`). Heartbeat alle 15 s. WebUI
  aktualisiert Status-Badges und Button-Zustände live.

- **FR-08:** `sdd hub status` zeigt im Terminal welche Projekte laufen und auf
  welchen Ports.

- **FR-09:** `sdd hub install` legt `~/.config/sdd/` an, schreibt
  `hub-registry.yaml` (leer) und `hub.yaml` (Default-Config inkl. Port 8080),
  schreibt die systemd-Unit-Datei, aktiviert den Service
  (`systemctl --user enable --now sdd-hub`) und registriert einen
  Avahi-Service (`/etc/avahi/services/sdd-hub.service`) damit der Hub
  unter `http://steamdeck.local:8080` erreichbar ist.

- **FR-10:** Stürzt ein Projektserver ab (Prozess beendet sich unerwartet),
  setzt `ProcessManager` den Status auf `error` und publiziert ein
  `StatusEvent`. Die WebUI zeigt den Error-Badge; ein Neustart erfolgt
  ausschließlich durch manuellen Klick auf "Start" in der WebUI.

## 5. User Stories

| ID    | Als …  | möchte ich …                                                                 | um …                                                               |
|-------|--------|------------------------------------------------------------------------------|--------------------------------------------------------------------|
| US-01 | Boris  | den Hub einmalig installieren und ihn danach vergessen                       | ihn nicht nach jedem Reboot manuell starten zu müssen              |
| US-02 | Boris  | alle Projekte in einer WebUI sehen                                           | ohne Terminal einen Überblick über laufende Server zu haben        |
| US-03 | Boris  | einen Projektserver per Klick aus der WebUI starten                          | keine SSH-Session oder Terminal auf dem Host brauchen zu müssen    |
| US-04 | Boris  | den Status jedes Projekts live aktualisiert sehen                            | sofort zu merken wenn ein Server gestoppt ist oder abstürzt        |
| US-05 | Boris  | `sdd hub register` einmalig pro Projekt aufrufen                             | Projekte nicht manuell in Konfigurationsdateien eintragen zu müssen|

## 6. Nicht-funktionale Anforderungen

| Kategorie    | Anforderung                                                                        |
|--------------|------------------------------------------------------------------------------------|
| Verfügbarkeit| Hub überlebt Reboot; systemd restart=on-failure mit 5 s Delay                     |
| Latenz       | SSE-Event erreicht WebUI ≤ 2 s nach Prozess-Statuswechsel                         |
| Robustheit   | SSE-Verbindungsabbruch → Browser reconnect automatisch (EventSource-Standard)     |
| Portabilität | Nur systemd-User-Services (kein root nötig)                                        |
| Sicherheit   | Kein Auth — Hub nur im lokalen Netz / VPN erreichbar; kein öffentliches Binding   |

## 7. Contracts

_(werden nach Review angelegt)_

## 8. Tests

_(werden nach Contract-Approval angelegt)_

## 9. Implementierungsreihenfolge

1. `ProjectEntry`-Schema + `ProjectRegistry` mit YAML-Persistenz (FR-02, FR-03)
2. `ProcessManager`: start/stop via subprocess + PID-tracking (FR-05, FR-06)
3. `StatusEventBus`: publish/subscribe für Prozess-Events (FR-07)
4. Hub FastAPI-App: `/projects`, `/projects/{id}/start`, `/projects/{id}/stop` (FR-03–FR-06)
5. SSE-Endpoint `/projects/stream` (FR-07)
6. `sdd hub register` + `sdd hub status` CLI-Kommandos (FR-02, FR-08)
7. WebUI-Seite `/projects`: Karten, Status-Badges, Start/Stop-Buttons (FR-04)
8. SSE-Integration in WebUI (live Status-Updates) (FR-07)
9. systemd-Unit-Datei + Avahi-Service-Datei + `sdd hub install` (FR-01, FR-09)

## 10. Offene Fragen

- [x] Auf welchem Port läuft der Hub standardmäßig? Konfigurierbar?
      → Port 8080 als Default; konfigurierbar via `.sdd/hub.yaml` (hub.port).
- [x] Wie wird der Hub im lokalen Netz erreichbar gemacht — reicht die
      IP des Hosts, oder ist ein mDNS/Avahi-Eintrag gewünscht?
      → mDNS/Avahi-Eintrag; Hub ist erreichbar unter `http://steamdeck.local:8080`.
      `sdd hub install` registriert den Avahi-Service.
- [x] Soll ein abgestürzter Projektserver automatisch neu gestartet werden
      (restart policy), oder nur Status=error anzeigen?
      → Nur Status=error anzeigen; Neustart erfolgt manuell per WebUI-Klick.
- [x] Registry-Datei: `~/.config/sdd/hub-registry.yaml` oder innerhalb des
      sdd-Projektverzeichnisses?
      → Globales Verzeichnis `~/.config/sdd/hub-registry.yaml`;
      wird automatisch durch `sdd hub install` angelegt.

## 11. Änderungshistorie

| Datum      | Version | Autor     | Änderung            |
|------------|---------|-----------|---------------------|
| 2026-06-06 | 0.1.0   | borisbrue | Initiale Erstellung |
| 2026-06-06 | 0.2.0   | borisbrue | Offene Fragen geklärt: Port 8080, mDNS/steamdeck.local, kein Auto-Restart, globale Registry via sdd hub install |
| 2026-06-06 | 0.3.0   | borisbrue | Regression-Fix: Alle Endpoints von /projects auf /hub/projects umbenannt (Namenskollision mit SPEC-0003) |
