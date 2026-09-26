---
id: SPEC-0058
title: "Rückbau abgelöster Ausführungspfade und Pipeline-Monitor"
type: feature
status: draft
owner: "Boris"
created: 2026-09-25
updated: 2026-09-26
version: 0.2.0
priority: medium
tags: [refactoring, pipeline, cleanup, cli]
depends_on: [SPEC-0053, SPEC-0059]
contracts: [CON-0210, CON-0211]
tests: [TST-0239, TST-0240]
---

# Rückbau abgelöster Ausführungspfade und Pipeline-Monitor

> **Status:** draft · **Owner:** Boris · **Version:** 0.2.0

## 1. Kontext & Motivation

Über mehrere Specs sind in sdd-framer parallele Wege entstanden, eine Spec in Code umzusetzen.
SPEC-0053 führt mit `sdd pipeline` einen allgemeinen Ablauf ein. Eine Bestandsaufnahme beim Review
(2026-09-26) hat gezeigt, dass ein Teil der alten Pfade tot oder defekt ist und ohne
Funktionsverlust wegfallen kann:

| Pfad | Zeilen | Zustand heute |
|------|-------:|---------------|
| `sub_agent.py`, `local_agent.py` (SPEC-0035/0036) | 514 | nirgends importiert; `local_agent` setzt `ANTHROPIC_API_KEY`/`ANTHROPIC_BASE_URL` |
| `autopilot.py` (SPEC-0037) | 310 | nirgends importiert; importiert ein nicht existierendes Modul, ruft entfernte Befehle auf |
| `distribute` mit `dist_orchestrator.py`, `review_pipeline.py`, `llm_pool.py` (SPEC-0026) | 436 | erzeugt keinen Code; `llm_pool` aus der Config wird nie gelesen |
| DAG-Monitor (`dag_command.py`, `dag_event.py`, Route `dag_monitor`) | ~400 | Route aktiv, aber niemand meldet Läufe an: die Seite ist immer leer |
| Web-Routen `/specs/{id}/implement`, `/evaluate` | – | rufen die seit SPEC-0044 entfernten Befehle `sdd implement`/`sdd evaluate` auf: immer Exit 1 |

Die lebendigen Pfade (`task_routing/` mit `task-route`/`task-exec`/`task-loop`, `sdd orchestrate`,
`/sdd-implement`) brauchen zuerst neue Fähigkeiten der Pipeline. Sie übernimmt SPEC-0061.

## 2. Zielsetzung

**Primärziel:** Toter und defekter Code der alten Ausführungspfade ist entfernt; die Web-UI zeigt
Pipeline-Runs an und startet sie über die CLI.

**Erfolgskriterien (messbar):**
- [ ] `sub_agent.py`, `local_agent.py`, `autopilot.py`, `dist_orchestrator.py`, `review_pipeline.py`,
      `llm_pool.py`, `dag_command.py` und `dag_event.py` sind entfernt; die Testsuite ist grün.
- [ ] Kein Code in `tool/` setzt `ANTHROPIC_API_KEY` oder `ANTHROPIC_BASE_URL`.
- [ ] Der Pipeline-Monitor der Web-UI zeigt einen Run von `sdd pipeline run` mit seinen Tasks.
- [ ] Die Baseline enthält keinen Eintrag mehr mit `fixed_by: SPEC-0058`.
- [ ] Netto-Reduktion des Codes; der PR weist Zeilen vorher/nachher aus.

**Nicht-Ziele (explizit):**
- Keine neuen Fähigkeiten der Pipeline (Session-Arbeitsrollen, `by_complexity`, `--auto`); das ist
  SPEC-0061.
- `task_routing/`, `sdd orchestrate`, `/sdd-implement` und der CodeGen-Pfad bleiben unverändert
  (SPEC-0061).
- Keine Anpassung der VS-Code-Extension; keine Änderung an den Quellen der Web-UI (die gebaute UI
  bleibt, die Routen liefern ihr bisheriges Format).

## 3. Architektur & Design Patterns

- **Adapter:** Abgelöste Befehle sind dünne Verweise ohne Logik; die Monitor-Route bildet
  Pipeline-Ereignisse auf das bisherige `DagEvent`-Format der UI ab.
- **Command** (SPEC-0053) und **Strategy** (Rollenbelegung) bleiben unverändert; sie tragen
  SPEC-0061.
- **Schichtung (ADR-0003):** Die Web-Schicht liest Runs nie direkt aus `.sdd/runs/`, sondern über
  eine Leseschnittstelle der CLI-Schicht (`sdd_cli.pipeline.monitor`, DIP-Befund aus dem Review).

## 4. Funktionale Anforderungen

- **FR-01:** `sub_agent.py`, `local_agent.py` und `autopilot.py` werden entfernt, dazu
  `SddConfig.autopilot_config()` und die zugehörigen Tests. Damit entfällt der einzige Code, der
  `ANTHROPIC_API_KEY`/`ANTHROPIC_BASE_URL` setzt, und der ARCH-04-Baseline-Eintrag für
  `local_agent.py`.
- **FR-02:** `dist_orchestrator.py`, `review_pipeline.py` und `llm_pool.py` werden entfernt;
  `sdd distribute` wird ein Verweis. Die Validierung von `llm_pool` in `config_manager.py` und der
  Wizard-Schritt dafür entfallen. `sdd task-status` und `sdd decompose` bleiben.
- **FR-03:** **Verweise.** Ein abgelöster Befehl nimmt seine bisherigen Argumente an, führt nichts
  aus (keinen LLM-Aufruf, keinen Git-Vorgang), nennt den Ersatz und endet mit Exit 1, nach der
  Konvention in `main.py` (`sdd implement`). Er wird in der Hilfe nicht mehr gelistet.
- **FR-04:** `sdd upgrade` kommentiert die nicht mehr gelesenen Config-Blöcke `llm_pool`,
  `local_agent` und `autopilot` aus (Inhalt bleibt als Kommentar erhalten) und meldet das.
- **FR-05:** **Leseschnittstelle für Runs.** `sdd_cli.pipeline.monitor` liefert die Runs eines
  Projekts (ID, Spec, Status, Phase, Zeitpunkt) und die Ereignisse eines Runs ab einem Offset. Die
  Ereignisse eines Tasks werden auf das `DagEvent`-Format abgebildet (`task_id`, `status`, `agent`,
  `model`, `details`). `sdd pipeline status RUN --json` gibt Zustand und offene Anfrage als JSON aus.
- **FR-06:** **Pipeline-Monitor.** Die Routen `GET /orchestrate/runs` und
  `GET /orchestrate/stream/{run_id}` lesen über FR-05 statt aus einem eigenen Ereignisbus. Der Stream
  sendet neue Ereignisse, sobald sie in `events.jsonl` stehen, und endet, wenn der Run nicht mehr
  läuft. Die Befehls-Route (`POST`) antwortet mit 410 und dem Hinweis auf `sdd pipeline decide`.
  `dag_command.py` und `dag_event.py` werden entfernt.
- **FR-07:** **Defekte Web-Routen.** `POST /specs/{id}/evaluate` startet `sdd holdout run
  --base-url … --spec`; `POST /specs/{id}/implement` startet `sdd pipeline run` im Hintergrund.
  Antwortformat (`{"ok", "output"}`) und Log-Stream bleiben wie bisher; der Run erscheint im
  Monitor.
- **FR-08:** **Baseline-Einträge.** Die Verfügbarkeitsprüfung von `claude` in den Web-Routen läuft
  über eine Funktion der LLM-Schicht (`llm.claude_available()`), nicht über `shutil.which("claude")`
  (ARCH-04). Tabellendefinition und Migration von `token_usage` liegen in der LLM-Schicht;
  `estimation.py` nutzt sie (ARCH-02). Der ARCH-01-Eintrag des CodeGen-Pfads bekommt
  `fixed_by: SPEC-0061`.
- **FR-09:** **Lifecycle.** `sdd spec deprecate SPEC-XXXX --reason "…" [--replaced-by SPEC-YYYY]`
  setzt `status: deprecated` und hält Grund und Nachfolger im Frontmatter und im Audit-Log fest.
  Die Contracts der Spec werden mit abgelöst, außer sie sind mit `--keep` ausgenommen;
  `sdd contract deprecate CON-XXXX --reason "…"` löst einen einzelnen Contract ab. SPEC-0026
  (mit `--keep CON-0097`), SPEC-0035, SPEC-0036 und SPEC-0037 werden damit auf `deprecated`
  gesetzt (Nachfolger SPEC-0053/SPEC-0058), CON-0103 (LLM-Pool-Schritt des Wizards) einzeln.

## 5. Nicht-funktionale Anforderungen

| Kategorie   | Anforderung |
|-------------|-------------|
| Migration   | Verweise bleiben mindestens zwei Minor-Versionen bestehen. |
| Umfang      | Netto-Reduktion des Codes, im PR mit Zeilen vorher/nachher ausgewiesen. |
| Keyfreiheit | Kein Pfad setzt `ANTHROPIC_API_KEY` oder `ANTHROPIC_BASE_URL`. |
| Monitor     | Neue Ereignisse erscheinen im Stream spätestens 2 s nach dem Schreiben. |

## 6. Akzeptanzkriterien (Gherkin)

```gherkin
Feature: Rückbau und Pipeline-Monitor

  Scenario: Alter Befehl verweist auf die Pipeline
    When ich "sdd distribute SPEC-0900" ausführe
    Then ist der Exit-Code 1
    And die Ausgabe nennt "sdd pipeline run"
    And es wird kein LLM aufgerufen und kein Git-Befehl ausgeführt

  Scenario: Monitor zeigt einen Pipeline-Run
    Given ein Run von "sdd pipeline run SPEC-0900" mit zwei Tasks
    When die Web-UI "/api/orchestrate/runs" abfragt
    Then enthält die Antwort den Run mit Spec und Status
    And der Stream des Runs liefert je Task Ereignisse im DagEvent-Format

  Scenario: Config-Aufräumen
    Given config.yaml enthält llm_pool und autopilot
    When ich "sdd upgrade" ausführe
    Then sind beide Blöcke auskommentiert und die Ausgabe meldet sie

  Scenario: Spec wird abgelöst
    When ich "sdd spec deprecate SPEC-0026 --reason 'abgelöst' --replaced-by SPEC-0053" ausführe
    Then hat SPEC-0026 den Status deprecated und nennt SPEC-0053 als Nachfolger
```

## 7. Edge Cases & Fehlerfälle

- Ein Projekt ohne `.sdd/runs/`: `/orchestrate/runs` liefert eine leere Liste, kein Fehler.
- Ein Run wird während des Streams abgebrochen: der Stream endet mit dem letzten Zustand.
- `sdd spec deprecate` auf eine Spec, von der andere nicht deprecated Specs abhängen: Warnung mit
  den abhängigen Specs, keine Blockade.
- `sdd upgrade` findet keinen der alten Blöcke: keine Änderung, keine Meldung.

## 8. Contracts (was wird garantiert)

| Contract-ID | Typ      | Was wird garantiert? |
|-------------|----------|----------------------|
| CON-0210    | behavior | Verweise, Config-Aufräumen, `sdd spec deprecate` |
| CON-0211    | behavior | Leseschnittstelle, Monitor-Routen und Web-Routen `implement`/`evaluate` |

## 9. Tests (wie wird verifiziert)

| Test-ID  | Level       | Was prüft der Test? |
|----------|-------------|---------------------|
| TST-0239 | acceptance  | Verweise, Upgrade, Deprecate |
| TST-0240 | acceptance  | Monitor und Web-Routen mit einem Pipeline-Run gegen den Fake-LLM-Server |

## 10. Offene Fragen

- [x] Schnitt: Rückbau hier, Pipeline-Erweiterungen und lebendige Pfade in SPEC-0061
      (entschieden 2026-09-26).
- [x] Verweise führen nichts aus (Hinweis, Exit 1), entschieden 2026-09-26.
- [x] DAG-Monitor wird auf das Pipeline-Protokoll umgebaut, nicht entfernt (entschieden 2026-09-26).
- [x] `/sdd-implement` bleibt als eigener Skill (entschieden 2026-09-25, umgesetzt in SPEC-0061).
- [x] VS-Code-Extension wird nicht angepasst (entschieden 2026-09-25).

## 11. Änderungshistorie

| Datum      | Version | Autor         | Änderung |
|------------|---------|---------------|----------|
| 2026-09-25 | 0.1.0   | Boris, Claude | Initiale Erstellung |
| 2026-09-26 | 0.2.0   | Boris, Claude | Review: geteilt in Rückbau (hier) und SPEC-0061; Verweise ohne Ausführung; Monitor auf Pipeline-Ereignisse; Baseline-Einträge; `sdd spec deprecate` |
