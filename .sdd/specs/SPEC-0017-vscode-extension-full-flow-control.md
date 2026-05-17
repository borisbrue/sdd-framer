---
id: SPEC-0017
title: "VS Code Extension – Full Flow Control & Dynamic Web UI"
project: PRJ-0001
status: review
owner: "Boris"
created: 2026-05-16
updated: 2026-05-16
version: 0.1.0
priority: high
tags: [vscode, web-ui, orchestration, dynamic-port, full-flow, developer-experience]
depends_on: [SPEC-0002, SPEC-0003, SPEC-0007, SPEC-0014, SPEC-0015, SPEC-0016]
contracts: [CON-0054, CON-0055, CON-0056]
tests: [TST-0060, TST-0061, TST-0062]
adrs: []
---

# VS Code Extension – Full Flow Control & Dynamic Web UI

> **Status:** draft · **Owner:** Boris · **Version:** 0.1.0

## 1. Kontext & Motivation

SPEC-0002 etablierte die grundlegende VS Code Extension: TreeView, Validierung,
Navigation und Befehlspalette für Dokument-CRUD. Seitdem sind mehrere mächtige
Features hinzugekommen, die ausschließlich über CLI oder Browser nutzbar sind:

- **Web UI** (SPEC-0003/0007): FastAPI + React auf Port 8000 – startet bisher nur manuell
  per `uvicorn`. Kein Weg, ihn aus VS Code heraus zu starten, zu stoppen oder zu öffnen.
- **Execute-Pipeline** (SPEC-0007): Der "Execute"-Button existiert nur im Browser.
- **Execution Gate / SOLID Quality Gate** (SPEC-0014/0015): Nur via `sdd` CLI.
- **Async AI Analysis** (SPEC-0016): Nur im Browser triggern/prüfen.
- **Contract Review / Estimation** (SPEC-0010/0011): Nur via `sdd` CLI.

Das Ergebnis: Entwickler verlassen VS Code mehrfach pro Feature-Zyklus. Dieses
Spec schließt die Lücke. Die Extension wird zur **primären Steuerzentrale** des
gesamten SDD-Flows.

## 2. Zielsetzung

**Primärziel:** Entwickler können den vollständigen SDD-Zyklus
(Spec anlegen → KI-Analyse → Review → Execute → Status verfolgen)
ohne VS Code zu verlassen durchführen.

**Erfolgskriterien (messbar):**
- [ ] `SDD: Start Web UI` startet FastAPI auf einem **freien Port** (OS-Zufallsport)
      und zeigt Port im Status Bar innerhalb 3 s an
- [ ] `SDD: Stop Web UI` beendet den Serverprozess sauber (kein Zombie-Prozess)
- [ ] Status Bar Item zeigt `SDD ⚡ :PORT` wenn Server läuft, `SDD ○` wenn gestoppt
- [ ] `SDD: Execute Spec` / `SDD: Execute Current Spec` starten die Orchestrator-Pipeline;
      Fortschritt erscheint im SDD Output Channel
- [ ] TreeView zeigt laufende Pipeline-Runs mit Spinner-Icon und aktuellem Step
- [ ] Alle neuen Befehle sind ohne Terminal nutzbar; das Terminal bleibt ein Opt-in

**Nicht-Ziele:**
- Kein eingebetteter Browser (WebView) für die React-SPA –
  System-Browser öffnen ist ausreichend und wartbarer
- Kein Multiplexing (mehrere Server-Instanzen gleichzeitig)
- Keine eigene Port-Konfigurationsoberfläche – `sdd.webUi.port` im VS Code Settings
- Kein Live-Log-Terminal innerhalb VS Code (Output Channel reicht)
- Keine eigene Auth-Schicht (identisch zu SPEC-0003: nur localhost)

## 3. Architektur

```
VS Code Extension (TypeScript)
  │
  ├── ServerManager (Singleton)
  │     ├── start(port: number | 0) → child_process.spawn('uvicorn', ...)
  │     │     port=0 → OS-Zufallsport via Python socket.bind(('',0))
  │     ├── stop() → proc.kill('SIGTERM') + SIGKILL-Fallback nach 3 s
  │     ├── getPort(): number | null
  │     └── getStatus(): 'running' | 'stopped' | 'starting' | 'error'
  │
  ├── StatusBarItem
  │     ├── "SDD ○"          → gestoppt (Klick → Start-Befehl)
  │     ├── "SDD ⟳ …"        → starting
  │     ├── "SDD ⚡ :54231"  → läuft (Klick → Browser öffnen)
  │     └── "SDD ✗"          → Fehler (Klick → Output Channel)
  │
  ├── PipelineClient (HTTP via node-fetch → localhost:PORT)
  │     ├── orchestrate(specId, opts) → POST /api/orchestrate
  │     ├── getPipelineRun(runId) → GET /api/pipeline/{run_id}
  │     ├── getActivePipeline(specId) → GET /api/pipeline/active?spec_id=X
  │     └── abortPipeline(runId) → POST /api/pipeline/{run_id}/abort
  │
  ├── TreeView (erweitert aus SPEC-0002)
  │     └── Pipeline-Run-Nodes: Spinner während running, ✓/✗ bei Terminal
  │
  └── OutputChannel "SDD"
        ├── Server-Logs (stdout/stderr von uvicorn)
        └── Pipeline-Fortschritt (polled alle 5 s)
```

### 3.1 Dynamischer Port

Der Extension-Befehl `SDD: Start Web UI` bestimmt den Port so:

```
1. Lese sdd.webUi.port aus VS Code Settings
   - Wert > 0  → verwende diesen fixen Port
   - Wert == 0 (default) → freien Port ermitteln

2. Freien Port ermitteln:
   python -c "import socket; s=socket.socket(); s.bind(('',0)); print(s.getsockname()[1]); s.close()"
   → Ausgabe: z.B. 54231

3. Starte uvicorn mit --port 54231
4. Speichere Port in ServerManager.getPort()
5. Aktualisiere StatusBarItem
```

Der Python-Aufruf nutzt dasselbe Python wie die `sdd`-CLI (aus `sdd.pythonPath`-
Einstellung). Fällt Python nicht verfügbar, wird 8000 als Fallback genutzt
(mit Fehlerwarnung falls belegt).

### 3.2 Server-Lifecycle

```
start() → Status: 'starting'
  → spawn: python -m uvicorn web.api.main:app --port PORT --host 127.0.0.1
  → warte auf "Application startup complete" in stdout (max 10 s)
  → Status: 'running' | 'error'

stop() → proc.kill('SIGTERM')
  → warte max 3 s auf exit
  → falls kein exit: proc.kill('SIGKILL')
  → Status: 'stopped'

Workspace close / Extension deactivate:
  → stop() automatisch aufrufen (kein Zombie)
```

VS Code Extension deactivate-Hook ruft `ServerManager.stop()` auf.

### 3.3 Pipeline-Execute aus VS Code

`SDD: Execute Current Spec` liest die Spec-ID aus dem YAML-Frontmatter des
aktuell geöffneten Editors (analog zur bestehenden Diagnose-Logik in
`diagnostics.ts`). Falls kein Frontmatter gefunden: Quick Pick mit allen
Specs aus der TreeView.

Pipeline-Fortschritt wird im Output Channel gepollt (alle 5 s). Das Polling
stoppt bei terminalem Status. Eine `vscode.window.withProgress`-Notification
zeigt den aktuellen Step in der Notification-Leiste (bottom right).

### 3.4 Neue VS Code Settings

| Setting                  | Typ     | Default | Beschreibung                                        |
|--------------------------|---------|---------|-----------------------------------------------------|
| `sdd.webUi.port`         | number  | 0       | 0 = dynamisch, >0 = fixer Port                      |
| `sdd.webUi.autoStart`    | boolean | false   | Server beim Öffnen eines SDD-Projekts automatisch starten |
| `sdd.webUi.openBrowser`  | boolean | true    | Browser nach Start automatisch öffnen               |
| `sdd.pipeline.pollInterval` | number | 5000  | Polling-Intervall für Pipeline-Status (ms)          |

## 4. Funktionale Anforderungen

### 4.1 Server-Management

- **FR-01:** `SDD: Start Web UI` – startet FastAPI auf freiem Port; deaktiviert
  wenn Server bereits läuft (stattdessen: Quick Pick "Neustarten / Öffnen / Abbrechen")
- **FR-02:** `SDD: Stop Web UI` – beendet Server; deaktiviert wenn gestoppt
- **FR-03:** `SDD: Restart Web UI` – Stop gefolgt von Start (nützlich nach Config-Änderungen)
- **FR-04:** `SDD: Open Web UI` – öffnet `http://localhost:PORT` im Systembrowser;
  startet Server zuerst wenn er gestoppt ist
- **FR-05:** Status Bar Item (rechte Seite, Priorität 100) zeigt Server-Status + Port;
  Tooltip zeigt vollständige URL und Python-Pfad

### 4.2 Pipeline Execute

- **FR-06:** `SDD: Execute Spec` – öffnet Quick Pick mit allen Specs die `status: approved`
  haben; startet Pipeline via `POST /api/orchestrate` (erfordert laufenden Server)
- **FR-07:** `SDD: Execute Current Spec` – liest ID aus aktueller Datei; zeigt Fehler
  wenn `status != approved`; zeigt Warnung wenn kein Server läuft (anbieten zu starten)
- **FR-08:** `SDD: Abort Pipeline` – Quick Pick mit laufenden Runs; sendet
  `POST /api/pipeline/{run_id}/abort`
- **FR-09:** Pipeline-Fortschritt via `vscode.window.withProgress` mit Cancel-Button;
  Fortschritts-Text zeigt `current_step` und Attempt-Nummer
- **FR-10:** Bei terminalem Status `labeled | merged`: VS Code Information Message
  mit klickbarem PR-Link; bei `failed`: Error Message mit Fehler-Zusammenfassung

### 4.3 Contract Review & Estimation

- **FR-11:** `SDD: Review Contract` – Input Box für CON-ID; ruft `sdd review-contract CON-XXXX`
  als Subprocess auf; Output erscheint im Output Channel
- **FR-12:** `SDD: Review Pending` – ruft `sdd review-pending`; mit Fortschritts-Notification
- **FR-13:** `SDD: Estimate Current Spec` – liest Spec-ID aus aktuellem Editor;
  ruft `sdd estimate SPEC-XXXX` auf; zeigt Ergebnis in Information Message (Kurzform)
  und Output Channel (vollständig)

### 4.4 TreeView-Erweiterungen

- **FR-14:** TreeView-Nodes für Specs mit `status: approved` zeigen einen ▶ "Execute"-
  Inline-Action-Button (erscheint bei Hover)
- **FR-15:** Läuft eine Pipeline für eine Spec, zeigt die Node einen Spinner
  und den `current_step`-Text als Description
- **FR-16:** Nach terminalem Status: ✓ (grün) oder ✗ (rot) Icon, PR-URL als
  klickbarer Tooltip

### 4.5 Weitere Flow-Befehle

- **FR-17:** `SDD: Status Check` – ruft `sdd status-check` auf; zeigt Ergebnis im Output Channel
- **FR-18:** `SDD: Validate` (bereits in SPEC-0002) – bleibt unverändert, wird in
  diese Spec als Inventar übernommen
- **FR-19:** `SDD: Obsidian Export` / `SDD: Obsidian Import` – wrappen
  `sdd obsidian export` / `sdd obsidian import`; Fortschritt im Output Channel

## 5. User Stories

| ID    | Als ...    | möchte ich ...                                                | um ...                                                |
|-------|------------|---------------------------------------------------------------|-------------------------------------------------------|
| US-01 | Entwickler | die Web UI per Befehl starten ohne Terminal                   | nicht aus dem Coding-Kontext heraus zu müssen         |
| US-02 | Entwickler | den laufenden Port im Status Bar sehen                        | schnell zu wissen ob der Server aktiv ist             |
| US-03 | Entwickler | die Web UI im Browser öffnen per Klick auf Status Bar         | sofort die UI nutzen zu können                        |
| US-04 | Entwickler | "Execute Current Spec" direkt aus dem Editor starten          | den Orchestrator ohne Browser zu triggern             |
| US-05 | Entwickler | den Pipeline-Fortschritt als VS Code Notification sehen       | den Status ohne Browser-Tab im Auge zu behalten       |
| US-06 | Entwickler | laufende Pipelines im TreeView erkennen                       | den Überblick über alle aktiven Runs zu haben         |
| US-07 | Entwickler | einen Pipeline-Run aus VS Code heraus abbrechen               | kein Browser-Tab öffnen zu müssen                     |
| US-08 | Entwickler | die Estimierung direkt aus dem Editor abrufen                 | Kostenabschätzungen ohne CLI-Wechsel zu bekommen      |
| US-09 | Entwickler | beim Schließen des Workspaces keinen Zombie-Prozess hinterlassen | keine blockierten Ports nach VS Code-Neustart zu haben |
| US-10 | Entwickler | den Server auf einem konfigurierbaren oder zufälligen Port starten | keine Port-Konflikte mit anderen lokalen Diensten zu haben |

## 6. Nicht-funktionale Anforderungen

| Kategorie    | Anforderung                                                                                |
|--------------|--------------------------------------------------------------------------------------------|
| Performance  | Server-Start-Erkennung < 10 s; Status Bar Update < 500 ms nach Start-Erkennung            |
| Ressourcen   | Polling läuft nur während einer aktiven Pipeline; kein Idle-Polling                        |
| Robustheit   | Server-Crash → Status Bar wechselt zu "SDD ✗"; deactivate-Hook immer aufgerufen           |
| Konfiguration | Alle Settings über `sdd.*`-Namespace in `package.json contributes.configuration`         |
| Kompatibilität | VS Code >= 1.85; Node.js built-ins (`child_process`, `net`) für Port-Logik             |
| Sicherheit   | Server nur auf `127.0.0.1` (nie `0.0.0.0`); keine externen Netzwerk-Interfaces           |
| Cleanup      | `deactivate()` in `extension.ts` ruft `ServerManager.dispose()` auf (SIGTERM + SIGKILL)  |

## 7. Akzeptanzkriterien (Gherkin)

```gherkin
Feature: Dynamic Web UI Start

  Scenario: Server auf freiem Port starten
    Given kein SDD-Server läuft
    And sdd.webUi.port ist auf 0 gesetzt
    When der Nutzer "SDD: Start Web UI" ausführt
    Then startet ein uvicorn-Prozess auf einem freien Port > 1024
    And das Status Bar Item zeigt "SDD ⚡ :<PORT>"
    And Output Channel zeigt "Server gestartet auf Port <PORT>"

  Scenario: Port-Konflikt mit fixem Port
    Given sdd.webUi.port ist auf 8000 gesetzt
    And Port 8000 ist bereits belegt
    When der Nutzer "SDD: Start Web UI" ausführt
    Then erscheint eine Error Message "Port 8000 ist belegt"
    And das Status Bar Item zeigt "SDD ✗"

  Scenario: Server-Stop ohne Zombie
    Given ein Server läuft auf Port 54231
    When der Nutzer "SDD: Stop Web UI" ausführt
    Then wird der Prozess innerhalb von 3 s beendet
    And Port 54231 ist danach wieder frei
    And das Status Bar Item zeigt "SDD ○"

Feature: Execute-Pipeline aus VS Code

  Scenario: Execute Current Spec – approved
    Given die aktuelle Datei ist SPEC-0007 mit status: approved
    And der SDD-Server läuft
    When der Nutzer "SDD: Execute Current Spec" ausführt
    Then wird POST /api/orchestrate { spec_id: "SPEC-0007" } gesendet
    And eine Fortschritts-Notification erscheint mit aktuellem Step
    And die TreeView-Node für SPEC-0007 zeigt Spinner + current_step

  Scenario: Execute Current Spec – nicht approved
    Given die aktuelle Datei ist SPEC-0005 mit status: draft
    When der Nutzer "SDD: Execute Current Spec" ausführt
    Then erscheint eine Warning Message "SPEC-0005 hat Status 'draft' – nur approved Specs können ausgeführt werden"
    And kein API-Request wird gesendet

  Scenario: Execute Current Spec – Server gestoppt
    Given die aktuelle Datei ist SPEC-0007 mit status: approved
    And der SDD-Server ist gestoppt
    When der Nutzer "SDD: Execute Current Spec" ausführt
    Then erscheint eine Information Message "SDD-Server läuft nicht. Jetzt starten?"
    And bei Bestätigung startet der Server und Execute beginnt danach

  Scenario: Pipeline erfolgreich abgeschlossen
    Given SPEC-0007 Pipeline-Run läuft
    When der Pipeline-Status wechselt auf "labeled"
    Then erscheint eine Information Message "SPEC-0007 implementiert – PR: <URL>"
    And TreeView-Node zeigt ✓-Icon

Feature: Workspace-Cleanup

  Scenario: VS Code wird geschlossen
    Given ein Server läuft auf Port 54231
    When VS Code den Workspace schließt
    Then ruft Extension deactivate() auf
    And der Server-Prozess wird beendet (SIGTERM, dann SIGKILL)
    And kein Prozess belegt Port 54231 nach dem Schließen
```

## 8. Contracts

| Contract-ID | Typ      | Was wird garantiert?                                                 |
|-------------|----------|----------------------------------------------------------------------|
| CON-0054    | behavior | Gherkin-Szenarien: Server-Start/Stop, Port-Ermittlung, Status Bar    |
| CON-0055    | behavior | Gherkin-Szenarien: Pipeline-Execute, Abort, Fortschritts-Anzeige    |
| CON-0056    | data     | JSON Schema für neue Extension-Settings (sdd.webUi.*, sdd.pipeline.*)|

## 9. Tests

| Test-ID  | Level      | Was prüft der Test?                                                    |
|----------|------------|------------------------------------------------------------------------|
| TST-0060 | unit       | ServerManager: Port-Ermittlung, start/stop/dispose, Status-Übergänge  |
| TST-0061 | unit       | PipelineClient: HTTP-Requests, Polling-Logik, Abort                    |
| TST-0062 | acceptance | Gherkin-Szenarien aus CON-0054 + CON-0055 im Extension-Host            |

## 10. Implementierungs-Reihenfolge

```
Phase A: ServerManager
  └─ vscode-extension/src/server.ts – ServerManager Singleton
       start(configuredPort): freien Port via Python ermitteln, uvicorn spawnen
       stop(): SIGTERM + SIGKILL-Fallback
       getPort(): number | null
       getStatus(): 'stopped' | 'starting' | 'running' | 'error'
       dispose(): stop() + cleanup
  └─ vscode-extension/src/statusBar.ts – StatusBarItem
       aktualisiert sich bei ServerManager-Events

Phase B: Pipeline-Integration
  └─ vscode-extension/src/pipeline.ts – PipelineClient
       orchestrate(), getPipelineRun(), getActivePipeline(), abortPipeline()
  └─ vscode-extension/src/extension.ts
       Neue Commands registrieren: StartWebUI, StopWebUI, RestartWebUI,
       OpenWebUI, ExecuteSpec, ExecuteCurrentSpec, AbortPipeline
       deactivate() → ServerManager.dispose()

Phase C: TreeView-Erweiterungen
  └─ vscode-extension/src/tree.ts
       approved-Specs: ▶ Inline-Action
       laufende Runs: Spinner + current_step in description
       terminale Runs: ✓/✗ Icon + PR-URL Tooltip

Phase D: CLI-Wrapper-Commands
  └─ vscode-extension/src/extension.ts
       ReviewContract, ReviewPending, EstimateCurrentSpec,
       StatusCheck, ObsidianExport, ObsidianImport

Phase E: Settings + package.json
  └─ vscode-extension/package.json
       contributes.configuration: sdd.webUi.*, sdd.pipeline.*
       contributes.commands: alle neuen Commands mit Icons
       contributes.menus: inline-Aktionen für TreeView
```

## 11. Offene Fragen

- [ ] Soll `sdd.webUi.autoStart` den Server beim ersten Öffnen eines SDD-Projekts
      automatisch starten? Default `false` ist sicherer, aber `true` wäre bequemer.
      → **Entscheidung ausstehend**
- [ ] Soll die Web UI in einer VS Code WebView (iframe) oder im System-Browser geöffnet werden?
      → **Vorschlag: System-Browser** (React SPA hat eigene Hot-Reload-Logik; WebView-Sicherheitseinschränkungen würden LocalStorage/EventSource verbieten)
- [ ] Sollen Pipeline-Runs über Extension-Neustarts hinweg persistent sein?
      → **Nein (v1):** In-Memory analog zur FastAPI-Seite; TTL-Verhalten identisch

## 12. Änderungshistorie

| Datum      | Version | Autor   | Änderung            |
|------------|---------|---------|---------------------|
| 2026-05-16 | 0.1.0   | Boris   | Initiale Erstellung |
| 2026-05-16 | 0.2.0   | Boris   | Implementiert: server.ts, pipeline.ts, tree.ts (Pfadfix + PipelineState), extension.ts (alle Commands), package.json (Settings + Menus) |
