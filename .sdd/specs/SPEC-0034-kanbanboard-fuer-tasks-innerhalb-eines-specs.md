---
id: SPEC-0034
title: "Kanban-Board für Tasks innerhalb eines Specs"
type: feature
status: review
owner: borisbrue
created: 2026-05-30
updated: 2026-06-03
version: 0.2.0
priority: medium
tags:
  - web-ui
  - kanban
  - task-tracking
  - realtime
  - token-tracking
depends_on:
  - SPEC-0003   # Web UI
  - SPEC-0026   # LLM Task Distribution Engine (task_model.py)
  - SPEC-0035   # Sub-Agenten-Delegation mit Token-Tracking
contracts:
  - CON-0123
  - CON-0124
tests:
  - TST-0144
  - TST-0145
  - TST-0146
adrs: []
---

# Kanban-Board für Tasks innerhalb eines Specs

> **Status:** review · **Owner:** borisbrue · **Version:** 0.2.0

## 1. Kontext & Motivation

Der `sdd-implement`-Skill zerteilt eine Spec nach dem Decompose-Schritt in Tasks
(`task_model.py`, `TaskStatus`). Diese Tasks werden heute nur in der CLI-Ausgabe
sichtbar — die Web UI zeigt keinen Echtzeit-Überblick.

Drei Fragen bleiben für den Entwickler unsichtbar:

1. **Welche Tasks sind geplant und wie abhängig sind sie voneinander?**
   Nach dem Decompose ist die Struktur nur im Transcript lesbar.
2. **Was passiert gerade?** Welcher Sub-Agent bearbeitet welchen Task?
   Die SPEC-0035-Implementation schreibt Token-Daten in `token-history`,
   aber der laufende Zustand ist nicht live abfragbar.
3. **Hat der Task sein Qualitätsziel erreicht?**
   Ein Task sollte erst als abgeschlossen gelten, wenn mindestens ein Test
   den implementierten Code grün verifiziert hat.

Das Kanban-Board macht Tasks, Zustände, Token-Kosten und Testabdeckung in der
Web UI live sichtbar.

## 2. Zielsetzung

**Primärziel:** Die Web UI zeigt pro Spec ein Kanban-Board mit allen Tasks,
ihrem Echtzeit-Status (SSE), der Token-Schätzung vor dem Start und dem
tatsächlichen Verbrauch danach. Ein Task gilt erst als `passed`, wenn
mindestens ein zugehöriger Test positiv durchgelaufen ist.

**Erfolgskriterien (messbar):**

- [ ] `GET /api/specs/{spec_id}/tasks` antwortet innerhalb 100 ms mit allen Tasks einer laufenden oder abgeschlossenen Implementation
- [ ] SSE-Event erreicht das Frontend innerhalb 500 ms nach jedem Task-Statuswechsel
- [ ] Kein Task wechselt nach `passed`, ohne dass sein zugehöriger Test grün ist
- [ ] Das Kanban-Board rendert korrekt für Specs mit 1–20 Tasks und 0–5 parallelen Gruppen

**Nicht-Ziele (explizit):**

- Keine manuelle Task-Erstellung oder -Bearbeitung über die UI (nur Lesezugriff)
- Kein Drag-and-Drop zur Statusänderung (Status ist rein durch den Agenten gesteuert)
- Keine Persistenz über mehrere Runs hinaus (pro Run eine `tasks.json`)
- Kein Multi-Spec-Überblick (Kanban ist spec-scoped)

## 3. User Stories

| ID    | Als ...        | möchte ich ...                                                               | um ...                                              |
| ----- | -------------- | ---------------------------------------------------------------------------- | --------------------------------------------------- |
| US-01 | Entwickler     | nach dem Decompose alle geplanten Tasks mit Schätz-Tokens sehen              | Aufwand und Kosten vor dem Start bewerten           |
| US-02 | Entwickler     | live sehen, welcher Task gerade läuft und von welchem Agenten                | den Fortschritt ohne CLI verfolgen                  |
| US-03 | Entwickler     | nach Abschluss die tatsächlichen Token pro Task sehen                        | die Schätzgenauigkeit über die Zeit kalibrieren     |
| US-04 | Entwickler     | sehen, welche Tasks parallel laufen (gleiche `parallel_group`)               | die Abhängigkeitsstruktur verstehen                 |
| US-05 | Entwickler     | sehen, ob der Testlauf eines Tasks grün war, bevor er als `passed` gilt      | Qualitätssicherung ohne manuelle Prüfung            |

## 4. Funktionale Anforderungen

- **FR-01:** `GET /api/specs/{spec_id}/tasks` gibt alle Tasks des letzten (oder laufenden) Runs zurück inkl. `estimated_tokens`, `actual_tokens` (falls vorhanden), `status`, `llm_id`, `parallel_group`, `test_ids`, `dependencies`.
- **FR-02:** `GET /api/specs/{spec_id}/tasks/events` liefert einen SSE-Stream. Jeder Task-Statuswechsel erzeugt ein `task_update`-Event mit dem vollständigen Task-Objekt.
- **FR-03:** Tasks persistieren in `.sdd/runs/{spec_id}/{run_id}/tasks.json` als JSON-Array. Jede Statusänderung schreibt die Datei neu (letzter Zustand, kein Append-Log).
- **FR-04:** Der Decompose-Schritt annotiert jeden Task mit `parallel_group: str | None`. Tasks ohne gemeinsame Dependencies und mit gleicher `parallel_group` werden parallel gestartet. Tasks ohne `parallel_group` laufen sequenziell.
- **FR-05:** Ein Task darf nur nach `passed` wechseln, wenn alle `test_ids` des Tasks erfolgreich ausgeführt wurden. Schlägt ein Test fehl, bleibt der Task auf `failed` mit dem Testfehler in `error_context`.
- **FR-06:** Die Web UI rendert ein Kanban-Board mit den Spalten: **Pending → Running → Review → Passed / Failed → Committed** (gemäß `TaskStatus` aus `task_model.py`).
- **FR-07:** Karten zeigen `estimated_tokens` (grau) vor dem Run. Nach Abschluss wird `actual_tokens` (blau) angezeigt, `estimated_tokens` wird durchgestrichen.
- **FR-08:** Eine Karte zeigt `parallel_group`-Label falls gesetzt und ein Abhängigkeits-Icon, wenn sie `dependencies` hat.
- **FR-09:** Beim Öffnen der Task-Ansicht wird automatisch ein SSE-Stream geöffnet. Wird der Stream unterbrochen, fällt die UI auf Polling (`GET /tasks`, 5 s) zurück, bis der Stream wieder verfügbar ist.

## 5. Nicht-funktionale Anforderungen

| Kategorie     | Anforderung                                                           |
| ------------- | --------------------------------------------------------------------- |
| Performance   | SSE-Event innerhalb 500 ms nach Statuswechsel; GET /tasks < 100 ms   |
| Security      | Kein direkter Dateisystemzugriff vom Frontend; alle Daten via API     |
| Accessibility | Kanban-Spalten per Tastatur navigierbar; ARIA-Labels auf Karten       |
| Observability | Jeder SSE-Event enthält `run_id` und `timestamp` für Tracing          |
| Datenschutz   | `error_context` enthält keinen Quellcode, nur Fehlermeldungen         |

## 6. Akzeptanzkriterien (Gherkin)

```gherkin
Feature: Task-Kanban-Board

  Scenario: Tasks erscheinen nach Decompose
    Given sdd-implement wurde für "SPEC-0034" gestartet
    When der Decompose-Schritt abgeschlossen ist
    Then liefert GET /api/specs/SPEC-0034/tasks mindestens einen Task
    And jeder Task hat status="pending"
    And jeder Task hat estimated_tokens > 0

  Scenario: Echtzeit-Update per SSE
    Given ein Task hat status="pending"
    And der SSE-Stream auf /api/specs/SPEC-0034/tasks/events ist offen
    When der Sub-Agent den Task startet
    Then sendet der SSE-Stream ein task_update-Event mit status="running"
    And das Event trifft innerhalb von 500ms ein
    And die Web UI aktualisiert die Kanban-Karte ohne Seitenreload

  Scenario: Task-Completion erfordert grünen Test
    Given ein Task hat test_ids=["TST-0001"] und status="review"
    When der Sub-Agent mark_passed() aufruft
    Then wird TST-0001 ausgeführt
    And bei Testerfolg wechselt status zu "passed"
    And bei Testfehler bleibt status="failed" mit Fehlermeldung in error_context

  Scenario: Parallele Tasks in gleicher Gruppe
    Given zwei Tasks haben parallel_group="group-1"
    And sie haben keine gegenseitigen dependencies
    When der Orchestrator die Gruppe startet
    Then werden beide Tasks gleichzeitig gestartet
    And beide zeigen status="running" zur gleichen Zeit im SSE-Stream

  Scenario: Tatsächliche Tokens nach Abschluss
    Given ein Task hat status="committed"
    And sub_agent hat actual_tokens=1234 nach Abschluss gespeichert
    When GET /api/specs/SPEC-0034/tasks aufgerufen wird
    Then enthält der Task actual_tokens=1234
    And estimated_tokens ist weiterhin vorhanden (für Vergleich)

  Scenario: SSE-Fallback auf Polling
    Given der SSE-Stream wurde unterbrochen
    When die UI den Verbindungsverlust erkennt
    Then startet die UI Polling alle 5 Sekunden auf GET /api/specs/{spec_id}/tasks
    And sobald SSE wieder verfügbar ist, stoppt das Polling
```

## 7. Edge Cases & Fehlerfälle

- **Zirkuläre Dependencies:** Werden beim Decompose erkannt (`decompose.py`). Betroffene Tasks erhalten `status=blocked`, `error_context` enthält "circular dependency detected". Die Implementierung startet nicht.
- **Kein laufender Run:** `GET /api/specs/{spec_id}/tasks` gibt `[]` zurück (kein 404), wenn noch kein Run gestartet wurde.
- **Mehrere Runs:** Der Endpoint gibt immer den letzten Run zurück (höchste `run_id` in `.sdd/runs/{spec_id}/`). Ältere Runs sind über `GET /api/specs/{spec_id}/runs` (FR außerhalb dieser Spec) erreichbar.
- **Sub-Agent-Crash:** Wenn ein Sub-Agent abstürzt, ohne `mark_failed()` aufzurufen, läuft der Watchdog-Timer (30 s) ab und setzt den Task auf `failed`.
- **Test-IDs leer:** Wenn `test_ids=[]`, darf `mark_passed()` nicht aufgerufen werden. Der Orchestrator blockiert den Übergang und loggt eine Warnung.

## 8. Contracts (was wird garantiert)

Diese Spec wird durch folgende Contracts maschinell prüfbar gemacht:

| Contract-ID | Typ      | Was wird garantiert?                                                    |
| ----------- | -------- | ----------------------------------------------------------------------- |
| CON-0123    | api      | GET /api/specs/{spec_id}/tasks – Response-Schema und SSE-Event-Format   |
| CON-0124    | behavior | Task-Completion-Gate: kein `passed` ohne grünen Test; test_ids Pflicht  |

## 9. Tests (wie wird verifiziert)

| Test-ID  | Level      | Was prüft der Test?                                           |
| -------- | ---------- | ------------------------------------------------------------- |
| TST-0144 | contract   | OpenAPI-Konformität GET /tasks gegen CON-0123                 |
| TST-0145 | acceptance | Gherkin-Szenarien aus Sektion 6 (Playwright + pytest-bdd)     |
| TST-0146 | unit       | parallel_group Dependency-Auflösung und Zirkel-Erkennung      |

## 10. Offene Fragen

- [ ] Soll `actual_tokens` direkt aus `token-history` gelesen werden oder schreibt der Sub-Agent-Orchestrator sie explizit in `tasks.json`? (Empfehlung: explizit in `tasks.json` — entkoppelt von `sdd calibrate`)
- [ ] Wie lang wird eine `tasks.json` aufbewahrt? (Vorschlag: 30 Tage, dann `sdd maintenance cleanup` entfernt sie)
- [ ] Soll der SSE-Stream auch `log`-Events (Subprozess-Output) weiterleiten oder nur Status-Events? (Empfehlung: nur Status-Events — Logs via CON-0071 WS-Logs-Endpoint)

## 11. Änderungshistorie

| Datum      | Version | Autor     | Änderung                              |
| ---------- | ------- | --------- | ------------------------------------- |
| 2026-05-30 | 0.1.0   | borisbrue | Initiale Erstellung (Draft)           |
| 2026-06-03 | 0.2.0   | borisbrue | Vollständige Ausarbeitung auf Basis SPEC-0026/0035-Infrastruktur |
