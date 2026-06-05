---
id: SPEC-0037
title: Agent-DAG-Monitor und autonomer Implementierungs-Autopilot
type: feature
status: implemented
owner: borisbrue
created: 2026-06-05
updated: '2026-06-05'
version: 0.3.0
priority: high
tags:
- webui
- dag-visualization
- auto-mode
- agent-monitor
- autonomous-pipeline
depends_on:
- SPEC-0036
- SPEC-0028
- SPEC-0034
- SPEC-0016
contracts: []
tests: []
adrs: []
started_at: '2026-06-05T12:13:57Z'
---
# Agent-DAG-Monitor und autonomer Implementierungs-Autopilot

## 1. Kontext & Motivation

SPEC-0036 führt parallele Sub-Agenten-Delegation mit DAG-Scheduler ein.
Die Ausführung ist bisher ausschließlich im Terminal sichtbar: kein Live-Feedback
in der WebUI, kein manueller Eingriff möglich, und der Zyklus endet nach
`sdd implement` — Review, Tests und Finalisierung müssen separat angestoßen werden.

SPEC-0028 (Interaktive Pipeline-Ausführung) definiert die bestehende Step-by-Step-
Pipeline mit manuellem Gate-Approval. SPEC-0037 erweitert dieses Modell in zwei
Richtungen: der Autopilot-Modus ersetzt die manuelle Schrittsteuerung durch eine
deterministisch gesteuerte State Machine, während der DAG-Monitor die Sicht auf
Einzel-Tasks innerhalb eines Schritts öffnet. SPEC-0028 bleibt die Basis für
Review- und Finalize-Integration; SPEC-0037 ruft deren Schnittstellen auf, ohne
sie zu ersetzen.

SPEC-0007 implementiert bereits einen asynchronen Orchestrator-Run mit SSE-Live-
Stream in der SpecDetail-Ansicht. SPEC-0037 erweitert diesen bestehenden Kanal
auf Task-Granularität (pro Task statt pro Phase) und fügt Command-Feedback hinzu —
es wird kein zweiter Transport-Layer eingeführt.

SPEC-0016 stellt die allgemeine Push-Benachrichtigungs-Infrastruktur (SSE/Job-Store)
bereit. SPEC-0037 nutzt diese Basis für Eskalations-Notifications.

SPEC-0004 definiert den autonomen Entwicklungs-Kreislauf als Level-4-Ziel
(Spec → Code → Test → Merge ohne Eingriff). SPEC-0037 implementiert dieses Ziel
für den `sdd implement`-Schritt — es ruft die bestehenden `sdd`-Schnittstellen
(test, review, finalize) auf und ersetzt keine davon.

Zwei Lücken:

1. **Observability:** Welcher Task läuft auf welchem Agenten? Wann ist Task-B
   bereit, weil Task-A gerade abschloss? Ist ein lokaler Proxy ausgefallen?
   Der Terminal-Output scrollt vorbei; keine interaktive Sicht auf den DAG.

2. **Autonomie:** Boris möchte `sdd implement --auto SPEC-XXXX` eingeben und
   zurückkommen wenn das Feature fertig — oder wenn ein unbehebbares Problem
   eskaliert. Heute muss er nach jedem Schritt manuell eingreifen.

Diese Spec schließt beide Lücken:
- **Agent-DAG-Monitor** (WebUI): interaktiver DAG-Graph, Echtzeit-Zustand,
  manuelle Overrides.
- **Autopilot-Modus** (`--auto`): vollständiger Zyklus mit Auto-Retry und
  Eskalation bei Stagnation.

## 2. Zielsetzung

**Primärziel:**
Boris startet `sdd implement --auto SPEC-XXXX` oder öffnet die WebUI während
einer laufenden Implementierung und sieht live, welcher Task auf welchem Agenten
läuft, kann eingreifen, und erhält eine WebUI-Benachrichtigung wenn der Autopilot
eskaliert.

**Erfolgskriterien (messbar):**
- [ ] WebUI zeigt DAG-Graph mit Echtzeit-Zustand (pending/running/done/failed)
      und Agent-Label pro Knoten innerhalb von 2 s nach Statuswechsel
- [ ] Nutzer kann per WebUI: Task pausieren, Agent-Routing überschreiben
      (force local / force cloud), Task neu starten, Task überspringen
- [ ] `sdd implement --auto SPEC-XXXX` durchläuft decompose → implement →
      test → review → finalize ohne manuelle Eingabe, solange Gates grün sind
- [ ] Bei Test-/Review-Fehler: bis zu `autopilot.max_fix_iterations` (default 3)
      automatische Fix-Zyklen vor Eskalation
- [ ] Eskalation erscheint als WebUI-Notification mit Fehlerdetails und
      Handlungsoptionen (retry / skip / abort)
- [ ] Alle Konfigurationsparameter in `.sdd/config.yaml` ohne Code-Änderung

**Nicht-Ziele (explizit):**
- Keine eigene DAG-Rendering-Library — Mermaid.js (bereits in WebUI vorhanden)
  oder einfacher D3-Canvas; kein vollständiges Graph-Framework (Cytoscape etc.)
- Kein Multi-User-/Kollaborations-Modus (nur Boris als Nutzer)
- Kein persistentes Replay von vergangenen Runs in der WebUI (nur laufende Session)
- Kein paralleler Autopilot für mehrere SPECs gleichzeitig
- Keine KI-basierte Entscheidung ob eskaliert wird — nur deterministisch:
  Iterationszähler + Fortschrittsprüfung
- Kein E-Mail/Push-Notification — nur WebUI-intern
- Kein Bypass des SPEC-0014-Qualitätsprozesses ohne explizites Opt-in:
  `automated_gate_approval` muss in `.sdd/config.yaml` auf `true` gesetzt sein;
  ohne dieses Flag stoppt der Autopilot an jedem Gate und wartet auf manuelle
  Bestätigung (SPEC-0014-konformes Verhalten bleibt der Default)

## 3. Architektur & Design Patterns

### Pattern 1 — Observer (Server-Sent Events)
> [Refactoring Guru – Observer](https://refactoring.guru/design-patterns/observer)

`DagScheduler` (SPEC-0036) publiziert Task-Completion-Events bereits intern.
Diese Events werden als Publisher in einen `DagEventBus` eingespeist. Der
`DagMonitorSSEHandler` (FastAPI `/orchestrate/stream/{run_id}`) ist Subscriber
und streamt die Events als Server-Sent Events (SSE) an die WebUI.

**Begründung:** SSE ist unidirektional (Server→Client), ausreichend für
Statusupdates, und benötigt keine WebSocket-Infrastruktur. Der `DagEventBus`
entkoppelt Scheduler von Transport-Layer — Scheduler muss nichts über HTTP wissen.

```python
class DagEvent(BaseModel):
    run_id: str
    task_id: str
    status: Literal["pending", "running", "done", "failed", "skipped", "paused"]
    agent: Literal["local", "cloud"]
    model: str
    timestamp: datetime

class DagEventBus:
    def publish(self, event: DagEvent) -> None: ...
    def subscribe(self, run_id: str) -> AsyncIterator[DagEvent]: ...
```

### Pattern 2 — Command
> [Refactoring Guru – Command](https://refactoring.guru/design-patterns/command)

Nutzereingriffe aus der WebUI (Pause, Override, Restart, Skip) werden als
`SchedulerCommand`-Objekte in eine `CommandQueue` geschrieben. Der
`DagScheduler` liest die Queue zwischen Task-Dispatches und wendet die
Commands an. Commands sind serialisierbar (Audit-Log) und rückgängig machbar
wo sinnvoll (Pause → Resume).

**Begründung:** Entkoppelt WebUI-Request-Handling von Scheduler-Logik.
Commands können geloggt, verzögert oder zurückgezogen werden ohne den
Scheduler-Loop zu blockieren. Kein direktes Mutieren von Scheduler-State
aus HTTP-Handlern heraus (kein Race Condition Risiko).

```python
class SchedulerCommand(Protocol):
    run_id: str
    task_id: str
    def apply(self, scheduler: DagScheduler) -> None: ...

class PauseTaskCommand:
    def apply(self, scheduler: DagScheduler) -> None:
        scheduler.pause_task(self.task_id)

class ForceRouteCommand:
    route: Literal["local", "cloud"]
    def apply(self, scheduler: DagScheduler) -> None:
        scheduler.override_route(self.task_id, self.route)
```

### Pattern 3 — State Machine (Autopilot)
> [Refactoring Guru – State](https://refactoring.guru/design-patterns/state)

Der Autopilot-Modus ist eine explizite State Machine mit den Zuständen:
`idle → decomposing → implementing → testing → reviewing → finalizing → done`
und den Fehlerzuständen `fix_loop` (automatischer Retry) und `escalated`
(Warten auf Nutzer-Entscheidung via WebUI).

**Begründung:** Die Transition-Logik (wann weiter, wann retry, wann eskalieren)
ist zustandsabhängig und würde ohne State Machine zu verschachtelten
`if/elif`-Blöcken degenerieren. State-Objekte kapseln je eine Phase und sind
einzeln testbar.

```
idle
  └─[start]─→ decomposing
                └─[dag_ready]─→ implementing
                                  └─[all_done]─→ testing
                                  |               └─[green]─→ reviewing
                                  |               |             └─[approved]─→ finalizing → done
                                  |               |             └─[rejected]─→ fix_loop
                                  |               └─[red]──→ fix_loop
                                  └─[task_failed]─→ fix_loop
fix_loop
  └─[iteration < max]─→ implementing (betroffene Tasks)
  └─[iteration >= max OR no_progress]─→ escalated
escalated
  └─[user: retry]─→ fix_loop (reset counter)
  └─[user: skip]──→ implementing (Task überspringen)
  └─[user: abort]─→ idle
```

### Datenfluss

```
sdd implement --auto SPEC-XXXX
    │
    ├── AutopilotStateMachine.start()
    │       │
    │       ├── [decomposing] sdd decompose → TaskDag
    │       │
    │       ├── [implementing] DagScheduler.run(dag) ← SPEC-0036
    │       │       │  publiziert DagEvents → DagEventBus
    │       │       │  liest SchedulerCommands aus CommandQueue
    │       │       │
    │       ├── [testing] sdd test SPEC-XXXX
    │       │
    │       ├── [reviewing] sdd review SPEC-XXXX (Claude self-review)
    │       │
    │       ├── [green] sdd finalize SPEC-XXXX → done
    │       │
    │       └── [red/failed] fix_loop → iterate oder escalate
    │
    └── WebUI /orchestrate/stream/{run_id}  ←── SSE ← DagEventBus
         /orchestrate/command/{run_id}      ──── POST Commands → CommandQueue
```

## 4. Funktionale Anforderungen

### WebUI Agent Monitor

- **FR-01:** `GET /orchestrate/runs` listet alle laufenden und die letzten 5
  abgeschlossenen Runs mit `run_id`, `spec_id`, `status`, `started_at`.

- **FR-02:** `GET /orchestrate/stream/{run_id}` ist ein SSE-Endpoint der
  `DagEvent`-Objekte streamt. Der Endpoint nutzt die bestehende SSE-Infrastruktur
  aus SPEC-0007 (selber Transport-Layer, erweitert auf Task-Granularität) und die
  Job-Push-Infrastruktur aus SPEC-0016 für Eskalations-Events. Die WebUI rendert
  daraus einen DAG-Graphen (Mermaid `graph LR` dynamisch generiert). Knoten-Farben:
  grau=pending, blau=running, grün=done, rot=failed, gelb=paused, durchgestrichen=skipped.

- **FR-03:** Jeder Knoten zeigt: `task_id`, Kurztitel, Agent-Badge
  (`LOCAL: llama3.1:8b` oder `CLOUD: claude-sonnet-4-6`), Dauer in Sekunden
  sobald running.

- **FR-04:** `POST /orchestrate/command/{run_id}` nimmt ein `SchedulerCommand`-JSON
  entgegen. Gültige Commands: `pause_task`, `resume_task`, `force_local`,
  `force_cloud`, `skip_task`, `restart_task`. `restart_task` ist nur für
  Tasks mit Status `failed` zulässig — bei anderen Stati wird der Command mit
  HTTP 422 abgelehnt. Command wird in `CommandQueue` geschrieben und innerhalb
  des nächsten Scheduler-Ticks ausgeführt.

- **FR-05:** Die WebUI-Seite `/orchestrate` zeigt die Run-Liste (FR-01) und
  öffnet bei Klick auf einen Run den Live-DAG. Keine Seitenladung nötig
  (SSE hält Verbindung offen). Der DAG-View enthält einen Link zur
  Kanban-Ansicht des jeweiligen Specs (`/specs/{spec_id}/tasks`, SPEC-0034),
  damit Nutzer zwischen Task-Ausführungsansicht und Task-Planungsansicht
  wechseln können.

### Autopilot-Modus

- **FR-06:** `sdd implement --auto SPEC-XXXX` startet den `AutopilotStateMachine`
  im Vordergrund. Ohne `--auto` ist das Verhalten identisch zu SPEC-0036
  (kein Breaking Change).

- **FR-12:** Ist `autopilot.automated_gate_approval: false` (Default) oder fehlt
  der Schlüssel, stoppt der Autopilot vor jedem SPEC-0014-Gate (testing → reviewing,
  reviewing → finalizing) und wartet auf `sdd spec approve` oder WebUI-Bestätigung —
  SPEC-0014-konformes Verhalten. Ist `automated_gate_approval: true`, prüft der
  Autopilot die Exit-Kriterien des Gates selbst (tests green / review approved) und
  führt `sdd spec approve` automatisch aus. Das Opt-in muss in `.sdd/config.yaml`
  explizit gesetzt werden; es gibt keine implizite Aktivierung durch `--auto` allein.

- **FR-07:** State `testing` ruft `sdd test SPEC-XXXX` auf und wertet den
  Exit-Code aus. Bei Exit 0: Transition nach `reviewing`. Bei Exit ≠ 0:
  Transition nach `fix_loop` mit fehlgeschlagenen Test-IDs als Kontext.

- **FR-08:** State `reviewing` startet einen Claude-Self-Review-Sub-Agenten
  (SPEC-0028-kompatibel). Gibt der Review `approved`: Transition nach `finalizing`.
  Gibt der Review `changes_requested` mit Findings: Transition nach `fix_loop`.

- **FR-09:** `fix_loop` inkrementiert `iteration_count`. Fortschritt wird
  gemessen als: mindestens ein vorher roter Test ist jetzt grün ODER ein
  Review-Finding wurde behoben. Kein Fortschritt AND `iteration_count >= max_fix_iterations`:
  Transition nach `escalated`.

- **FR-10:** `escalated`-Zustand schreibt eine `EscalationEvent` in `DagEventBus`
  und wartet auf `SchedulerCommand` (retry / skip / abort) aus der WebUI.
  Die Notification erscheint als persistenter Banner (nicht Toast) mit den
  drei Aktionsbuttons — bleibt sichtbar bis zur expliziten Nutzer-Entscheidung.
  Im Terminal: blockierender Prompt als Fallback falls WebUI nicht offen ist.

- **FR-11:** Alle Autopilot-Transitionen werden in `token-history` als
  `autopilot_event` mit Phase, Iteration und Gate-Ergebnis geloggt.

## 5. Konfigurationsschema

```yaml
# .sdd/config.yaml
autopilot:
  max_fix_iterations: 3              # Maximale Auto-Fix-Zyklen vor Eskalation
  review_model: "claude-sonnet-4-6"  # Modell für Self-Review-Phase
  test_timeout_seconds: 300          # Timeout für sdd test pro Iteration
  progress_check: true               # Fortschritts-Check vor Eskalation
  notify_on_escalation: true         # WebUI-Notification bei Eskalation
  automated_gate_approval: false     # Opt-in: SPEC-0014-Gates automatisch passieren
                                     # wenn Exit-Kriterien erfüllt; Default false (manuell)

dag_monitor:
  sse_heartbeat_seconds: 15          # SSE Keep-Alive-Intervall
  max_runs_history: 5                # Abgeschlossene Runs in /runs-Liste
```

## 6. User Stories

| ID    | Als …  | möchte ich …                                                                    | um …                                                                 |
|-------|--------|---------------------------------------------------------------------------------|----------------------------------------------------------------------|
| US-01 | Boris  | im Browser sehen welche Tasks gerade auf welchen Agenten laufen                 | Routing-Entscheidungen nachvollziehen ohne Terminal-Scrollen          |
| US-02 | Boris  | per Klick einen Task auf Cloud forcen wenn der lokale Proxy überlastet ist      | die Implementierung nicht manuell neu starten zu müssen              |
| US-03 | Boris  | `sdd implement --auto SPEC-XXXX` starten und später zurückkommen               | nicht jeden Schritt manuell anstoßen zu müssen                       |
| US-04 | Boris  | eine WebUI-Benachrichtigung erhalten wenn der Autopilot nicht weiterkommt       | gezielt eingreifen zu können ohne den Terminal zu beobachten          |
| US-05 | Boris  | im Eskalationsfall per WebUI "retry", "skip" oder "abort" klicken               | die Entscheidung dort treffen wo ich gerade arbeite                   |

## 7. Nicht-funktionale Anforderungen

| Kategorie     | Anforderung                                                                              |
|---------------|------------------------------------------------------------------------------------------|
| Latenz        | SSE-Event erreicht WebUI ≤ 2 s nach Task-Statuswechsel im Scheduler                     |
| Robustheit    | SSE-Verbindungsabbruch → Browser reconnect automatisch (EventSource-Standard)            |
| Korrektheit   | Commands aus WebUI dürfen DAG-Invarianten nicht verletzen (skip nur wenn keine Deps offen)|
| Observability | Jede Autopilot-Transition loggt: phase, gate_result, iteration, timestamp                |
| Security      | CommandQueue akzeptiert nur lokal authentifizierte Requests (Session-Cookie aus SPEC-0028)|

## 8. Akzeptanzkriterien (Gherkin)

```gherkin
Feature: Agent-DAG-Monitor WebUI

  Scenario: Live-DAG zeigt Agent-Zuordnung
    Given sdd implement SPEC-XXXX läuft (ohne --auto)
    And WebUI /orchestrate ist im Browser geöffnet
    When Task-3 von LocalSubAgentProxy übernommen wird
    Then erscheint Knoten Task-3 in blau mit Label "LOCAL: llama3.1:8b"
    And Aktualisierung erfolgt innerhalb von 2 s

  Scenario: Nutzer forcet Cloud für laufenden Task
    Given Task-5 hat status="running" mit agent="local"
    When Nutzer "force cloud" für Task-5 klickt
    Then wird ForceRouteCommand in CommandQueue geschrieben
    And Scheduler übernimmt Task-5 mit CloudSubAgentProxy beim nächsten Tick

Feature: Autopilot-Modus

  Scenario: Grüner Durchlauf ohne Eingriff
    Given SPEC-XXXX hat 4 Tasks, alle Tests grün nach Implementierung
    And Review gibt "approved" zurück
    When sdd implement --auto SPEC-XXXX ausgeführt wird
    Then läuft Zyklus decompose → implement → test → review → finalize durch
    And kein Nutzer-Eingriff erforderlich

  Scenario: Eskalation nach max_fix_iterations
    Given autopilot.max_fix_iterations = 3
    And Tests schlagen in jeder Iteration fehl ohne Fortschritt
    When Iteration 3 abgeschlossen ist
    Then wechselt Autopilot in Zustand "escalated"
    And WebUI zeigt Notification mit Fehlerdetails und Optionen retry/skip/abort

  Scenario: Fortschritts-Check verhindert endlose Schleife
    Given fix_loop läuft, aber kein Test wird besser
    When progress_check = true und iteration_count < max_fix_iterations
    Then eskaliert Autopilot trotzdem (kein Fortschritt erkannt)
```

## 9. Contracts

| Contract-ID | Typ      | Was wird garantiert?                                                           |
|-------------|----------|--------------------------------------------------------------------------------|
| CON-0130    | data     | `DagEvent`-Schema: Pflichtfelder, Status-Enum, Agent-Enum                      |
| CON-0131    | api      | SSE-Endpoint `/orchestrate/stream/{run_id}`: Event-Format, Reconnect-Verhalten |
| CON-0132    | behavior | `SchedulerCommand`-Protocol: apply-Semantik, DAG-Invarianz-Prüfung             |
| CON-0133    | behavior | `AutopilotStateMachine`-Transitionen: deterministisch, Iterationszähler        |

## 10. Tests

| Test-ID  | Level    | Was prüft der Test?                                                              |
|----------|----------|----------------------------------------------------------------------------------|
| TST-0152 | unit     | `DagEventBus` publish/subscribe — Event-Ordering, run_id-Isolation              |
| TST-0153 | unit     | `CommandQueue` apply — DAG-Invarianz bei skip (offene Deps → reject)             |
| TST-0154 | unit     | `AutopilotStateMachine` — alle Transitionen, Iterationszähler, Fortschritts-Check|
| TST-0155 | contract | SSE-Endpoint — Event-Format, Content-Type: text/event-stream, Heartbeat          |
| TST-0156 | contract | `SchedulerCommand`-Schema — Pflichtfelder, unbekannte Commands → 422             |

## 11. Implementierungsreihenfolge

1. `DagEvent`-Schema + `DagEventBus` (Pub/Sub, run_id-isoliert) (FR-02, CON-0130)
2. `DagScheduler` (SPEC-0036) um `DagEventBus.publish()`-Aufrufe erweitern
3. SSE-Endpoint `GET /orchestrate/stream/{run_id}` (FR-02, CON-0131)
4. `GET /orchestrate/runs` (FR-01)
5. WebUI-Seite `/orchestrate`: Run-Liste + DAG-Render via Mermaid (FR-03, FR-05)
6. `SchedulerCommand`-Protocol + Commands (Pause/Resume/ForceRoute/Skip/Restart) (FR-04)
7. `CommandQueue` + `POST /orchestrate/command/{run_id}` (FR-04, CON-0132)
8. WebUI Command-Buttons (Pause, Force Local/Cloud, Skip, Restart) (FR-04)
9. `AutopilotStateMachine` mit States + Transitionen (FR-06–FR-09, CON-0133)
10. `fix_loop`: Fortschritts-Check + Iterationszähler (FR-09)
11. `escalated`: EscalationEvent + WebUI-Notification + Terminal-Fallback (FR-10)
12. Autopilot-Token-History-Logging (FR-11)
13. Konfigurationsschema + Contracts + Tests

## 12. Offene Fragen

- [x] Welches Mermaid-Diagramm-Layout für den DAG? → `graph LR` (links→rechts) fest.
- [x] Soll `restart_task` einen bereits `done`-Task nochmals ausführen? → Nur für `failed`-Tasks; `done`-Tasks sind unveränderlich.
- [x] Soll die Eskalations-Notification als Toast oder persistenter Banner erscheinen? → Persistenter Banner mit Aktionsbuttons retry/skip/abort; bleibt bis zur Nutzer-Entscheidung sichtbar.

## 13. Änderungshistorie

| Datum      | Version | Autor      | Änderung            |
|------------|---------|------------|---------------------|
| 2026-06-05 | 0.1.0   | borisbrue  | Initiale Erstellung |
| 2026-06-05 | 0.2.0   | borisbrue  | Review-Findings: SPEC-0028-Abgrenzung in §1, FR-05 Kanban-Link (SPEC-0034) |
| 2026-06-05 | 0.3.0   | borisbrue  | Regression-Findings: SPEC-0007/SPEC-0016-Infrastruktur referenziert (FR-02), SPEC-0004-Abgrenzung §1, SPEC-0014-Konflikt gelöst via FR-12 automated_gate_approval Opt-in |
