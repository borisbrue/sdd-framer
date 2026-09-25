---
id: SPEC-0058
title: "Konsolidierung der Ausführungspfade auf sdd pipeline"
type: feature
status: draft
owner: "Boris"
created: 2026-09-25
updated: 2026-09-25
version: 0.1.0
priority: medium
tags: [refactoring, pipeline, cleanup, cli]
depends_on: [SPEC-0053, SPEC-0059]
contracts: []
tests: []
---

# Konsolidierung der Ausführungspfade auf sdd pipeline

> **Status:** draft · **Owner:** Boris · **Version:** 0.1.0

## 1. Kontext & Motivation

Über mehrere Specs sind in sdd-framer parallele Wege entstanden, eine Spec in Code umzusetzen. Sie
überschneiden sich, sind teils nie verdrahtet und teils defekt:

| Pfad | Herkunft | Zustand heute |
|------|----------|---------------|
| `/sdd-implement` (Skill) | Blueprint | Claude implementiert selbst; ruft `sdd decompose`, `sdd task-route`, `sdd task-exec` |
| `sdd task-exec`, `sdd task-route` | SPEC-0045 | Einzeltask lokal; Retry-Bug bei vorhandener Datei (BEFUND §2) |
| `sdd task-loop` | SPEC-0045 (uncommittet) | headless TDD-Schleife mit Eskalation |
| `sdd distribute`, `task-status` | SPEC-0026 | erzeugt **keinen** Code; `gh` ohne Absicherung; PR-Titel hart „SPEC-0026“ |
| `sdd orchestrate` | SPEC-0004 | Dark Factory: Code in einem Schritt, Holdout-Eval, Retry, Auto-Merge; Web-Route `orchestrate` |
| `sub_agent.py` | SPEC-0035 | nicht an die CLI angebunden; Token-Datensätze immer 0 |
| `local_agent.py`, `DagScheduler` | SPEC-0036 | nicht an die CLI angebunden; setzt `ANTHROPIC_API_KEY` für einen Proxy |
| `autopilot.py`, `dag_command.py` | SPEC-0037 | Autopilot nicht angebunden, importiert ein nicht existierendes Modul; DAG-Monitor in der Web-UI |
| `review_pipeline.py`, `llm_pool.py` | SPEC-0026 | nur von `distribute` genutzt; Reviewer ohne Provider, wird übersprungen |

Zusammen sind das rund 2700 Zeilen mit eigener Routing-, Retry-, Review- und Token-Logik. SPEC-0053
führt mit `sdd pipeline` einen allgemeinen Ablauf mit Rollen, Gates, Supervisor und Protokoll ein.
Diese Spec bildet jeden Pfad darauf ab oder entfernt ihn.

## 2. Zielsetzung

**Primärziel:** Es gibt genau einen Ausführungspfad, `sdd pipeline`. Jeder andere Einstieg (Skills,
Web-UI, Dark Factory) ist eine Konfiguration dieses Pfads.

**Erfolgskriterien (messbar):**
- [ ] Kein Modul außerhalb von `tool/sdd_cli/pipeline/` enthält eigene Retry-, Routing- oder
      Eskalationslogik für Tasks. Das prüft eine Regel in `architecture.yaml` von sdd-framer (SPEC-0054, SPEC-0059).
- [ ] Die Module `sub_agent.py`, `local_agent.py`, `autopilot.py`, `dist_orchestrator.py`,
      `review_pipeline.py`, `llm_pool.py` und `task_routing/` sind entfernt oder in die Pipeline
      überführt. Die Testsuite ist danach grün.
- [ ] `/sdd-implement`, `/sdd-supervise`, `sdd orchestrate` und die Web-UI schreiben alle in dasselbe
      Run-Protokoll (`.sdd/runs/…`) und erscheinen in `sdd pipeline report`.
- [ ] Kein Code liest oder setzt `ANTHROPIC_API_KEY` außer dem expliziten Provider `anthropic`.

**Nicht-Ziele (explizit):**
- Keine neuen Fähigkeiten über SPEC-0053 hinaus.
- Die Holdout-Evaluation selbst (`evaluator.py`, `holdout_runner.py`) bleibt unverändert und wird nur
  als Abschluss-Gate eingebunden.
- Die VS-Code-Extension wird nicht angepasst. Der Fokus für Editor-Integration liegt künftig auf
  sddit. Nutzt die Extension einen entfernten Befehl, bleibt der versteckte Verweis ihre Brücke.

## 3. Architektur & Design Patterns

### Eine Pipeline, mehrere Belegungen
Unterschiede zwischen den bisherigen Pfaden werden zu Konfiguration:

| Einstieg | Belegung |
|----------|----------|
| `/sdd-supervise` | alle Arbeitsrollen = Modelle aus `llm.roles`, `supervisor: session` |
| `/sdd-implement` | `test_author` und `implementer` = `session` (Claude Code schreibt im Dialog), übrige Rollen aus `llm.roles` |
| `sdd orchestrate` (Dark Factory) | alle Rollen headless, `supervisor: claude-cli`, Abschluss-Schritte `finalize`, `holdout`, `automerge` aktiv |
| Web-UI | startet `sdd pipeline run` und liest `events.jsonl` (DAG-Monitor) |

Dafür akzeptiert jede Rolle (nicht nur `supervisor`) den Modus `session` mit dem Anfrage- und
Antwortmechanismus aus SPEC-0053 FR-15. Bei Arbeitsrollen schreibt die Session die Dateien selbst,
und die Pipeline prüft danach die Gates.

### Routing nach Komplexität als Rollenoption
Das Routing aus SPEC-0045 (`complexity_threshold`) wird eine Option der Rollenbelegung, statt eigene
Befehle zu brauchen:

```yaml
llm:
  roles:
    implementer:
      by_complexity: { low: qwen35-a3b-mlx, medium: qwen38-27b, high: session }
```

### Strangler Fig
Alte Befehle werden zu versteckten Verweisen (bestehende Konvention in `main.py`, z. B.
`test-run`), und die Module dahinter werden entfernt, sobald die Pipeline ihre Aufgabe übernommen
hat. `sdd upgrade` migriert die Config.

## 4. Funktionale Anforderungen

- **FR-01:** Jede Rolle akzeptiert `mode: session` (analog zum Supervisor-Modus aus SPEC-0053).
  Arbeitsrollen im Modus `session` erhalten statt eines LLM-Aufrufs eine persistierte Anfrage
  (Task, Kontext, erlaubte Pfade laut PathPolicy). Die Session schreibt die Dateien und bestätigt mit
  `sdd pipeline decide RUN_ID --done TASK_ID`. Die Pipeline wertet danach die Gates aus, wie bei
  jedem anderen Modus.
- **FR-02:** `llm.roles.<rolle>.by_complexity` ordnet `low|medium|high` je ein Modellprofil zu. Die
  Komplexität kommt aus der Task-Klassifikation des `decomposer`.
- **FR-03:** `/sdd-implement` wird auf `sdd pipeline run` mit der Belegung aus Abschnitt 3
  umgeschrieben. Die Schritte „decompose“, „task-route“ und „task-exec“ entfallen aus dem Skill.
- **FR-04:** `sdd orchestrate` wird zu `sdd pipeline run --auto`. Das Flag aktiviert die
  Abschluss-Schritte Finalize (PR), Holdout-Gate mit Retry-Kontext und Auto-Merge nach
  Autonomie-Level. `sdd orchestrate` bleibt als versteckter Verweis bestehen. Die Web-Route
  `orchestrate` startet die Pipeline.
- **FR-05:** Folgende Befehle werden zu versteckten Verweisen:
  - `task-exec` → `sdd pipeline run --task ID`
  - `task-route` → `sdd pipeline run --dry-run`
  - `task-loop` → `sdd pipeline run`
  - `distribute` → `sdd pipeline run --auto`
  - `task-status` → `sdd pipeline status`
  - `decompose` → `sdd pipeline run --dry-run`
- **FR-06:** Entfernt werden `sub_agent.py`, `local_agent.py`, `autopilot.py`, `dist_orchestrator.py`,
  `review_pipeline.py`, `llm_pool.py`, `task_routing/` (Routing-Logik in FR-02 überführt) sowie
  zugehörige Tests. Tests, die weiterhin gültiges Verhalten prüfen, werden auf die Pipeline
  umgestellt.
- **FR-07:** Der DAG-Monitor der Web-UI (`dag_command.py`, Route `dag_monitor`) liest
  `events.jsonl` der Pipeline statt eigener Zustände.
- **FR-08:** `sdd upgrade` migriert `task_routing`, `llm_pool` und `local_agent` aus `config.yaml`
  nach `llm.roles` bzw. `llm.profiles`. Nicht abbildbare Einträge werden als Kommentar erhalten und
  gemeldet.
- **FR-09:** Die Specs SPEC-0026, SPEC-0035, SPEC-0036, SPEC-0037 und SPEC-0045 werden über den
  Lifecycle der CLI auf `deprecated` gesetzt, mit Verweis auf SPEC-0053/SPEC-0058. SPEC-0004 bleibt
  `implemented` und bekommt einen Hinweis, dass die Umsetzung jetzt in der Pipeline liegt.
- **FR-10:** In `architecture.yaml` von sdd-framer kommt eine Regel, die das Ergebnis absichert:
  Aufrufe von `get_code_gen_provider`/`get_completion_provider` für Task-Arbeit gibt es nur unter
  `tool/sdd_cli/pipeline/**`.

## 5. Nicht-funktionale Anforderungen

| Kategorie   | Anforderung                                                               |
|-------------|---------------------------------------------------------------------------|
| Migration   | Versteckte Verweise bleiben mindestens zwei Minor-Versionen bestehen.     |
| Umfang      | Netto-Reduktion des Codes; der Report zur Umsetzung weist Zeilen vorher/nachher aus. |
| Keyfreiheit | Nach der Konsolidierung setzt kein Pfad `ANTHROPIC_API_KEY` oder `ANTHROPIC_BASE_URL`. |

## 6. Akzeptanzkriterien (Gherkin)

```gherkin
Feature: Ein Ausführungspfad

  Scenario: Alter Befehl verweist auf die Pipeline
    When ich "sdd task-exec SPEC-0900 t-1" ausführe
    Then erscheint ein Hinweis auf "sdd pipeline run --task t-1"
    And es wird kein LLM aufgerufen

  Scenario: sdd-implement nutzt die Pipeline
    Given llm.roles.implementer.mode ist session
    When /sdd-implement SPEC-0900 einen Task bearbeitet
    Then enthält .sdd/runs/SPEC-0900/<run>/events.jsonl den Task mit role=implementer und mode=session
    And die Gates aus SPEC-0054 wurden nach der Bearbeitung ausgewertet

  Scenario: Config-Migration
    Given config.yaml enthält task_routing.enabled true und llm.local_llm
    When ich "sdd upgrade" ausführe
    Then enthält config.yaml llm.roles.implementer.by_complexity
    And task_routing ist als migriert kommentiert
```

## 7. Edge Cases & Fehlerfälle

- Offene Runs aus `task-loop` oder `distribute` beim Upgrade: werden nicht migriert; `sdd upgrade`
  meldet sie mit Pfad.
- Die Web-UI eines älteren Projekts ruft die Route `orchestrate`: Sie funktioniert weiterhin über die
  Pipeline.
- Ein Session-Task wird nie bestätigt: `sdd pipeline status` zeigt ihn als `awaiting_session`;
  `--resume` setzt dort fort.

## 8. Contracts (was wird garantiert)

| Contract-ID | Typ      | Was wird garantiert?                                          |
|-------------|----------|---------------------------------------------------------------|
| CON-XXXX    | behavior | Verweise der abgelösten Befehle                               |
| CON-XXXX    | data     | Config-Migration `task_routing`/`llm_pool`/`local_agent` → `llm.roles`/`llm.profiles` |
| CON-XXXX    | behavior | Modus `session` für Arbeitsrollen                             |

## 9. Tests (wie wird verifiziert)

| Test-ID  | Level       | Was prüft der Test?                                         |
|----------|-------------|-------------------------------------------------------------|
| TST-XXXX | unit        | `by_complexity`-Auflösung, Config-Migration                  |
| TST-XXXX | integration | Session-Arbeitsrolle mit Fake-Session; `--auto` mit Fake-Finalize/Holdout |
| TST-XXXX | acceptance  | Gherkin-Szenarien aus Abschnitt 6                           |

## 10. Offene Fragen

- [x] `/sdd-implement` bleibt als eigener Skill mit fester Belegung (entschieden 2026-09-25).
- [x] VS-Code-Extension → wird nicht angepasst; Fokus liegt auf sddit (entschieden 2026-09-25).

## 11. Änderungshistorie

| Datum      | Version | Autor         | Änderung            |
|------------|---------|---------------|---------------------|
| 2026-09-25 | 0.1.0   | Boris, Claude | Initiale Erstellung |
