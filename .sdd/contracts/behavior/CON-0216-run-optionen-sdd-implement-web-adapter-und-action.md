---
id: CON-0216
title: "Run-Optionen, sdd-implement, Web-Adapter und Action"
type: behavior
format: gherkin
spec: SPEC-0062
version: 0.2.1
status: approved
artifact: ".sdd/contracts/behavior/run-optionen-sdd-implement-web-adapter-und-action.feature"
tests: ["TST-0245"]
---

# Contract: Run-Optionen, sdd-implement, Web-Adapter und Action

> **Spec:** SPEC-0062 · **Typ:** Verhalten (Gherkin) · **Status:** approved

## Zweck

Legt fest, wie die Einstiege die Pipeline belegen: die Run-Optionen `--session` und `--steps`, der Skill `/sdd-implement`, die Web-Route `orchestrate` als Adapter, `sdd start --auto` und die GitHub-Action-Vorlage (SPEC-0062 FR-01 bis FR-04, FR-08).

## Garantien

Die Szenarien im Artifact (`.sdd/contracts/behavior/run-optionen-sdd-implement-web-adapter-und-action.feature`) sind **ausführbare Spezifikation**.
Jedes Szenario MUSS durch einen automatisierten Test (pytest) abgedeckt sein. Die Web-Route wird mit dem FastAPI-TestClient geprüft; der Prozess `sdd pipeline run` läuft gegen den Fake-LLM-Server. Skill- und Action-Text werden als Dateien geprüft.

## Invarianten

- **INV-01:** `sdd pipeline run --session ROLLE` (mehrfach) belegt die genannten Rollen für diesen Run mit Modus `session`; die Belegung steht unter `options.session` in `run.json` und gilt auch bei `--resume`. `config.yaml` bleibt unverändert. Eine unbekannte Rolle ergibt Exit 2.
- **INV-02:** `--steps` (kommagetrennt, nur `holdout`, `finalize`, `automerge`) ersetzt `pipeline.auto_steps` für den Run und steht unter `options.steps` in `run.json`; ohne `--auto` oder mit unbekanntem Schritt Exit 2.
- **INV-03:** `/sdd-implement` startet nach Vorbedingungen, Review/Approve und Holdout-Anlage genau `sdd pipeline run SPEC --auto --session test_author --session implementer --session supervisor` und setzt bei Exit 3 mit `sdd pipeline done` (Arbeitsauftrag) bzw. `sdd pipeline decide` (Entscheidung) fort. Er enthält weder `task-route`, `task-exec`, `sdd decompose` noch `sdd finalize`. Repo-Kopie (`.claude/commands/sdd-implement.md`) und Blueprint sind identisch, abgesehen vom `scope:`-Frontmatter, das alle Repo-Skills tragen (TST-0196).
- **INV-04:** Die Web-Endpunkte `POST /api/orchestrate`, `GET /api/pipeline/active`, `GET /api/pipeline/{id}`, `GET /api/pipeline/{id}/log` und `POST /api/pipeline/{id}/abort` behalten Pfade, Statuscodes und Felder nach CON-0021 in Version 0.4.0. Die `run_id` der Antwort ist die Run-ID der Pipeline. `project_id`, `force` und `override_reason` behalten ihre Bedeutung (Gate-Prüfung vor dem Start).
- **INV-05:** Hinter `POST /api/orchestrate` läuft `sdd pipeline run SPEC --auto` als eigener Prozess; `dry_run` wird zu `--dry-run`, `no_pr` zu `--steps holdout`, `base_url` zu `--base-url`. Das Log besteht aus den Ausgabezeilen; `report.pr_url` kommt aus dem Ereignis `finalize`, `report.pass_rate` aus `holdout`. `abort` beendet den Prozess, der Status wird `aborted`. Wartet der Run auf eine Session-Rolle (Exit 3), ist der Status `paused` und das Log nennt `sdd pipeline decide` bzw. `done`. `POST /api/run` mit `cmd: orchestrate` und der Chat-Intent `orchestrate SPEC` führen `sdd pipeline run SPEC --auto` aus; Push-Typen (CON-0077) bleiben.
- **INV-06:** `sdd start SPEC --auto` startet `sdd pipeline run SPEC --auto` und gibt dessen Exit-Code weiter; ohne `--auto` bleibt `sdd start` unverändert.
- **INV-07:** Die GitHub-Action-Vorlage (Repo und Blueprint) ruft `sdd pipeline run $SPEC --auto`, nicht `sdd orchestrate`; `ANTHROPIC_API_KEY` ist kein Pflicht-Secret mehr und nur für `provider: anthropic` dokumentiert.

## Begriffe

| Begriff | Definition |
|---------|------------|
| Session-Rolle | Rolle im Modus `session`: Claude Code bearbeitet die Anfrage im Dialog (SPEC-0061) |
| Adapter | übersetzt das alte Web-Format auf `sdd pipeline run`, ohne eigene Ausführungslogik |
