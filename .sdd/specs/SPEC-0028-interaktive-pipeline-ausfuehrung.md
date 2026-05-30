---
id: SPEC-0028
title: Interaktive Pipeline-Ausführung im Web UI
status: implemented
owner: Boris
created: 2026-05-19
updated: '2026-05-21'
version: 0.2.0
priority: high
tags:
- pipeline
- web-ui
- gate
- ai-agent
- contracts
- tests
- holdouts
depends_on:
- SPEC-0027
contracts:
- CON-0108
- CON-0109
- CON-0110
tests:
- TST-0127
- TST-0128
- TST-0129
adrs: []
started_at: '2026-05-21T13:04:46Z'
---
## 1. Zweck & Überblick

Die SDD Web UI zeigt seit SPEC-0027 einen Pipeline-Flowchart mit Gate-Phasen.
Die Buttons lösen bisher nur Statusmarkierungen aus — keine echten Aktionen.
Ein Developer soll direkt im Browser jeden Schritt des SDD-Workflows ausführen
können: Spec reviewen lassen, Contracts vorschlagen und editieren, Tests und
Holdouts erzeugen, Entwicklung starten, Tests im Container ausführen und den
Commit abschließen. Der KI-Agent (aktuell Claude, konfigurierbar) übernimmt
die inhaltliche Arbeit; der Mensch prüft, editiert und gibt frei.

## 2. Akzeptanzkriterien

### Gate-Aktionen & UI-Verhalten

- [ ] Jeder Gate-Button löst eine echte Aktion aus und zeigt das Ergebnis inline
- [ ] **Spec-Review:** Agent analysiert die Spec, liefert strukturiertes Feedback (Lücken, Widersprüche, fehlende Anforderungen) direkt im UI
- [ ] **Contracts vorschlagen:** Agent erzeugt Contract-Entwürfe als `.md`-Dateien in `.sdd/contracts/` und verknüpft sie mit der Spec
- [ ] **Contract-Review:** Konfliktanalyse läuft, Ergebnis mit offenen Punkten wird angezeigt; Contracts können inline editiert werden (mit Agent-Hilfe)
- [ ] **Tests generieren:** Test-Stubs werden in `tests/` abgelegt
- [ ] **Holdouts erzeugen:** Szenarien entstehen isoliert — ausschließlich auf Basis der Contracts, kein Sourcecode-Kontext
- [ ] **Holdouts editieren:** Holdout-Dateien können inline editiert werden mit Agent-Hilfestellung
- [ ] **sdd start:** Git-Branch wird angelegt, Container gestartet
- [ ] **Tests im Container:** `pytest` läuft im Container, Ergebnis erscheint im UI
- [ ] **sdd finalize:** Commit + PR werden erstellt, PR-Link erscheint im UI
- [ ] Agent ist per `.sdd/config.yaml` (LLM-Pool) austauschbar

### Funktionale Anforderungen

- [ ] **FR-01:** `POST /api/specs/{id}/review` — Agent reviewt Spec, speichert Feedback in `.sdd/reviews/{id}-review.md`, gibt `{ok, summary, issues[]}` zurück
- [ ] **FR-02:** `POST /api/specs/{id}/propose-contracts` — Agent schlägt Contracts vor, schreibt `.md`-Dateien, verknüpft Frontmatter, gibt `{ok, contracts[]}` zurück
- [ ] **FR-03:** `POST /api/gate/{id}/contract-review` — bestehender Endpunkt, Ergebnis wird im UI angezeigt
- [ ] **FR-04:** `POST /api/specs/{id}/generate-tests` — bestehender `test-generate`-Endpunkt, Ergebnis wird inline angezeigt
- [ ] **FR-05:** `POST /api/specs/{id}/generate-holdouts` — Agent erzeugt Holdout-Szenarien ausschließlich auf Contract-Basis (kein Sourcecode)
- [ ] **FR-06:** `GET/PUT /api/specs/{id}/contracts/{cid}` — Contract inline lesen und speichern; `POST /api/specs/{id}/contracts/{cid}/assist` für Agent-Hilfe
- [ ] **FR-07:** `GET/PUT /api/specs/{id}/holdouts/{hid}` — Holdout inline lesen und speichern; `POST /api/specs/{id}/holdouts/{hid}/assist` für Agent-Hilfe
- [ ] **FR-08:** `POST /api/specs/{id}/start` — bestehender Endpunkt, startet Branch + Container
- [ ] **FR-09:** `POST /api/specs/{id}/run-tests` — führt `pytest` im Container aus, gibt Output zurück
- [ ] **FR-10:** `POST /api/specs/{id}/finalize` — bestehender Endpunkt, Commit + PR
- [ ] **FR-11:** `GET /api/specs/{id}/job` — Polling-Endpunkt für laufende Jobs
- [ ] **FR-12:** Agent-Provider wird aus LLM-Pool in `.sdd/config.yaml` gewählt

### User Stories

**US-01 (Developer im Browser):**
> Als Developer möchte ich auf „Spec Review starten" klicken und innerhalb von
> 30 Sekunden strukturiertes Feedback sehen, damit ich Lücken beheben kann
> bevor Contracts entstehen.

**US-02 (Developer im Browser):**
> Als Developer möchte ich vorgeschlagene Contracts direkt im Browser editieren
> und dabei Fragen an den Agenten stellen, damit ich keine externe IDE öffnen muss.

**US-03 (Developer im Browser):**
> Als Developer möchte ich „Tests im Container" klicken und das pytest-Ergebnis
> im UI sehen, damit ich den Entwicklungsfortschritt ohne Terminal verfolgen kann.

**US-04 (Agent):**
> Als KI-Agent möchte ich Holdouts ausschließlich auf Basis von Contracts erzeugen,
> damit die Evaluator-Isolation gewahrt bleibt.

## 3. Constraints & Non-Goals

### Nicht-Ziele

- Kein LLM-Provider-Wechsel im UI (bleibt Config)
- Kein Multi-Spec-Batch-Betrieb gleichzeitig
- Kein manuelles Editieren von Specs im Browser
- Kein Echtzeit-Streaming (Polling reicht, Long-Polling optional)
- Kein eigenes Secret-Management im UI

### Architektur & Design Patterns

#### Command Pattern
[Refactoring Guru – Command](https://refactoring.guru/design-patterns/command)

Jede Gate-Aktion wird als `PipelineCommand`-Objekt modelliert: `execute()`,
`rollback()`, `status()`. Das ermöglicht Retry-Logik, Logging und spätere
Parallelisierung ohne Änderung am UI-Code.

**Begründung:** Die Aktionen (Review, Propose, Generate, Start, Finalize) haben
unterschiedliche Implementierungen aber ein einheitliches Interface — klassischer
Command-Anwendungsfall.

#### Strategy Pattern
[Refactoring Guru – Strategy](https://refactoring.guru/design-patterns/strategy)

Der KI-Agent ist eine austauschbare Strategie (`AgentStrategy`): `ClaudeAgent`,
`OpenAIAgent`, `OllamaAgent`. Der LLM-Pool aus der Config wählt die aktive
Strategie zur Laufzeit.

**Begründung:** Der Agent ist variabel (laut Boris konfigurierbar). Strategy
isoliert die Provider-spezifische Logik vom Pipeline-Controller.

#### Observer Pattern (für Long-Polling)
[Refactoring Guru – Observer](https://refactoring.guru/design-patterns/observer)

Laufende Aktionen schreiben ihren Fortschritt in eine Job-Status-Datei
(`.sdd/pipeline/{spec_id}-job.json`). Das Frontend pollt `/api/specs/{id}/job`
und zeigt Zwischenstände an — ohne WebSocket.

**Begründung:** Einfacher als WebSocket, kompatibel mit der bestehenden
Uvicorn-Infrastruktur, ausreichend für die erwarteten Latenzanforderungen.

## 4. Abhängigkeiten

Voraussetzung: SPEC-0027 (Pipeline-Flowchart mit Gate-Phasen im Web UI)

### Contracts

| ID | Titel | Typ |
|----|-------|-----|
| CON-0108 | Interactive Pipeline KI-Aktionen API | api |
| CON-0109 | Job-Status Polling API | api |
| CON-0110 | Contract- und Holdout-Inline-Editor API | api |

**CON-0108** definiert das `{ok, output}`-Response-Schema aller KI-Aktions-Endpunkte sowie ihre Nebeneffekte (Gate-Phase-Markierung, Datei-Schreiben).

**CON-0109** definiert das Job-Status-Schema für den Polling-Endpunkt inkl. aller Status-Werte (`idle`, `running`, `done`, `failed`).

**CON-0110** definiert die CRUD-Operationen für Contract- und Holdout-Inline-Editing sowie das Assist-Request/-Response-Format.

### Tests

| ID | Titel | Stufe | Artifact |
|----|-------|-------|---------|
| TST-0127 | JobManager Unit-Tests | unit | `tests/unit/test_pipeline_jobs.py` |
| TST-0128 | Interactive API KI-Aktionen Unit-Tests | unit | `tests/unit/test_interactive_routes.py` |
| TST-0129 | Interactive API CRUD + Container Unit-Tests | unit | `tests/unit/test_interactive_routes.py` |

Alle 22 Unit-Tests sind implementiert und grün (791 passed, 0 failed im Gesamtprojekt).

## 5. Notizen

### Implementierungsreihenfolge

1. `AgentStrategy` + `ClaudeAgent` (FR-12) — Basis für alle KI-Aktionen
2. `PipelineCommand` Basisklasse + Job-Status-Datei (FR-11)
3. Spec-Review Endpunkt + UI-Anzeige (FR-01)
4. Contract-Vorschlag Endpunkt + UI-Verknüpfung (FR-02)
5. Contract-Editor + Agent-Assist (FR-06)
6. Test-Generierung Endpunkt (FR-04)
7. Holdout-Generierung Endpunkt (FR-05)
8. Holdout-Editor + Agent-Assist (FR-07)
9. Run-Tests im Container (FR-09)
10. Finalize / PR (FR-10, bestehend verdrahten)

### Offene Fragen

- Soll der Spec-Review Änderungen direkt in die `.md`-Datei schreiben oder nur Feedback ausgeben?
- Wie lange darf ein Job laufen bevor ein Timeout greift (Vorschlag: 120s)?
- Sollen Contract-Edits versioniert werden (Git-Snapshots)?

### Änderungshistorie

| Version | Datum      | Änderung                                    | Autor |
|---------|------------|---------------------------------------------|-------|
| 0.1.0   | 2026-05-19 | Initiale Erstellung                         | Boris |
| 0.2.0   | 2026-05-20 | Contracts + Tests ergänzt, Implementierung  | Boris |