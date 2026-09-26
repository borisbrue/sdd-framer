---
id: SPEC-0062
title: "Ablösung von task-routing, orchestrate und sdd-implement durch die Pipeline"
type: feature
status: draft
owner: "Boris"
created: 2026-09-26
updated: 2026-09-26
version: 0.2.0
priority: medium
tags: [pipeline, refactoring, cleanup, skill]
depends_on: [SPEC-0061, SPEC-0058, SPEC-0059]
contracts: []
tests: []
---

# Ablösung von task-routing, orchestrate und sdd-implement durch die Pipeline

> **Status:** draft · **Owner:** Boris · **Version:** 0.2.0

## 1. Kontext & Motivation

Seit SPEC-0061 kann `sdd pipeline` alles, was die alten Ausführungspfade leisten. Diese Spec stellt
die Einstiege um und entfernt die alten Pfade:

| Pfad | Zustand | Ersatz |
|------|---------|--------|
| `task_routing/` (924 Zeilen), `task-route`, `task-exec`, `task-loop` | aktiv (`task_routing.enabled: true`), `/sdd-implement` ruft es auf | `llm.profiles` + `by_complexity`, `--task`, `sdd pipeline run` |
| `orchestrator.py` (536 Zeilen), `sdd orchestrate`, `sdd start --auto` | aktiv | `sdd pipeline run --auto` |
| Web-Route `POST /api/orchestrate` und `/api/pipeline/{id}` (Execute-Button) | aktiv | dieselbe Route als Adapter vor `sdd pipeline run --auto` |
| CodeGen-Pfad (`get_code_gen_provider`, `CodeGenProvider`, Schreiben in `openai_compat.py`) | nur von den Pfaden oben genutzt | Rollen `test_author`/`implementer` |
| `llm_probe.py` | seit SPEC-0061 ungenutzt | `sdd config test-llm` |
| `/sdd-implement` (Repo-Kopie v0.9 und Blueprint v0.7 auseinandergelaufen) | Claude implementiert, ruft `task-route`/`task-exec` | `sdd pipeline run` mit test_author, implementer, supervisor im Modus `session` |
| GitHub-Action-Vorlage `sdd-orchestrate.yml` | ruft `sdd orchestrate` | `sdd pipeline run --auto` |

## 2. Zielsetzung

**Primärziel:** Es gibt genau einen Ausführungspfad, `sdd pipeline`. `/sdd-implement`, die Web-UI,
`sdd start --auto` und die GitHub-Action sind Belegungen dieses Pfads.

**Erfolgskriterien (messbar):**
- [ ] `task_routing/`, `orchestrator.py`, der CodeGen-Pfad und `llm_probe.py` sind entfernt; die
      Testsuite ist grün; der PR weist die Zeilen vorher/nachher aus.
- [ ] `task-route`, `task-exec`, `task-loop` und `orchestrate` sind Verweise (Hinweis, Exit 1).
- [ ] `/sdd-implement`, die Web-UI und `sdd start --auto` erzeugen Runs unter `.sdd/runs/`.
- [ ] `sdd arch check` ist grün mit der neuen Regel ARCH-05; die Baseline hat keinen Eintrag mit
      `fixed_by: SPEC-0061` oder `SPEC-0062`.

**Nicht-Ziele (explizit):**
- Keine neuen Pipeline-Fähigkeiten außer den Run-Optionen `--session` und `--steps`, die die
  Einstiege brauchen.
- Keine Änderung an den Quellen der Web-UI und keine Anpassung der VS-Code-Extension.

## 3. Architektur & Design Patterns

Angenommen (Review 2026-09-26):
- **Adapter:** Verweise, die Web-Route und die Config-Migration übersetzen nur, ohne eigene
  Ausführungslogik.
- **Strategy:** Die Einstiege unterscheiden sich nur in der Rollenbelegung (Profil, `by_complexity`,
  `session`).
- **Factory Method:** Mit CodeGen-Pfad und `llm_probe.py` entfällt die zweite Erzeugungslinie für
  Provider; es bleibt `llm/factory.py` (ARCH-03).
- **Facade:** Nach außen gibt es nur `sdd pipeline` (CLI, `monitor`, `store`, `schemas`, `roles`,
  `path_policy`). ARCH-05 verbietet allen anderen Schichten den Zugriff auf die Interna der Pipeline
  (DIP-Befund aus SPEC-0061).

## 4. Funktionale Anforderungen

- **FR-01:** **Run-Optionen.** `sdd pipeline run SPEC --session ROLLE` (mehrfach) belegt die Rolle nur
  für diesen Run mit `session`; die Belegung steht in `run.json`, `config.yaml` bleibt unverändert.
  `--steps holdout,finalize,automerge` überschreibt `pipeline.auto_steps` für einen Run mit `--auto`.
- **FR-02:** **`/sdd-implement`** führt Vorbedingungen, Review/Approve und Holdout-Anlage wie bisher
  aus und startet dann `sdd pipeline run SPEC --auto --session test_author --session implementer
  --session supervisor` (decomposer und reviewer aus `llm.roles`). Bei Exit 3 liest der Skill die
  offene Anfrage (`pending-decision.json` oder `pending-work.json`), arbeitet sie ab (entscheiden
  bzw. Test oder Code schreiben) und setzt mit `sdd pipeline decide` bzw. `sdd pipeline done` fort,
  bis der Run endet. Die Schritte `sdd decompose`, `task-route`, `task-exec`, der eigene TDD-Zyklus
  und `sdd finalize` entfallen aus dem Skill. Repo-Kopie (`.claude/commands/`) und Blueprint sind
  danach identisch.
- **FR-03:** **Web-Route als Adapter.** `POST /api/orchestrate`, `GET /api/pipeline/active`,
  `GET /api/pipeline/{id}`, `GET /api/pipeline/{id}/log` und `POST /api/pipeline/{id}/abort` behalten
  Pfade, Anfrage- und Antwortformate. Dahinter läuft `sdd pipeline run SPEC --auto` als Prozess
  (`dry_run` → `--dry-run`, `no_pr` → `--steps holdout`, `base_url` → `--base-url`); das Log sind
  die Ausgabezeilen, der `report` kommt aus dem Run-Protokoll (`pr_url` aus `finalize`,
  `pass_rate` aus `holdout`).
- **FR-04:** **`sdd start --auto`** startet `sdd pipeline run --auto` statt des Orchestrators.
- **FR-05:** **Verweise.** `task-route`, `task-exec`, `task-loop` und `orchestrate` nehmen ihre
  bisherigen Argumente an, führen nichts aus, nennen den Ersatz und enden mit Exit 1 (Konvention aus
  SPEC-0058).
- **FR-06:** **Entfernen.** `task_routing/`, `orchestrator.py`, `llm_probe.py`, der CodeGen-Pfad
  (`get_code_gen_provider`, `CodeGenProvider`, `CodeGenResult`, `RecordingCodeGenProvider`,
  `ClaudeCliCodeGenProvider`, `OpenAICompatCodeGenProvider`) und die zugehörigen Tests. Der
  ARCH-01-Eintrag für `openai_compat.py` verschwindet aus der Baseline.
- **FR-07:** **Config-Migration.** `sdd upgrade` übernimmt `llm.local_llm` als Profil
  `llm.profiles.lokal` und ordnet bei `task_routing.enabled: true` die Stufen, deren Score die
  Schwelle nicht überschreitet (low = 15, medium = 50, high = 80), in
  `llm.roles.implementer.by_complexity` diesem Profil zu. Danach kommentiert es `task_routing` und
  `llm.local_llm` aus (`# [SPEC-0062] …`) und meldet alles. Gibt es schon `llm.profiles.lokal` oder
  `llm.roles.implementer.by_complexity`, wird nichts überschrieben, sondern gemeldet.
- **FR-08:** **GitHub-Action-Vorlage** ruft `sdd pipeline run $ID --auto`; `ANTHROPIC_API_KEY` ist
  nur noch ein optionales Secret für Projekte, die `provider: anthropic` ausdrücklich wählen.
- **FR-09:** **Lifecycle.** SPEC-0045 und ihre Contracts werden über `sdd spec deprecate` abgelöst
  (Nachfolger SPEC-0061); CON-0012 (Orchestrator aus SPEC-0004) über `sdd contract deprecate`.
- **FR-10:** **Architektur.** `.sdd/architecture.yaml` bekommt die Schicht `pipeline`
  (`tool/sdd_cli/pipeline/**`) und die Regel ARCH-05 mit ADR-0006: Außerhalb von `pipeline` und
  `entry` importiert niemand `mediator`, `runner`, `steps`, `gates`, `providers`, `decisions` oder
  `context` der Pipeline.
- **FR-11:** **Doku.** README und `.sdd/SDD-REFERENCE.md` beschreiben die Verweise und die Pipeline
  als einzigen Pfad.

## 5. Nicht-funktionale Anforderungen

| Kategorie   | Anforderung |
|-------------|-------------|
| Migration   | Verweise bleiben mindestens zwei Minor-Versionen bestehen. |
| Umfang      | Netto-Reduktion des Codes, im PR mit Zeilen vorher/nachher ausgewiesen. |
| Keyfreiheit | Kein Pfad setzt `ANTHROPIC_API_KEY`; die Action verlangt ihn nur bei `provider: anthropic`. |

## 6. Akzeptanzkriterien (Gherkin)

```gherkin
Feature: Ein Ausführungspfad

  Scenario: Alter Befehl verweist auf die Pipeline
    When ich "sdd task-exec SPEC-0900 T01" ausführe
    Then ist der Exit-Code 1 und die Ausgabe nennt "sdd pipeline run SPEC-0900 --task T01"

  Scenario: Web-UI startet die Pipeline
    When die Web-UI "POST /api/orchestrate" mit spec_id SPEC-0900 aufruft
    Then läuft "sdd pipeline run SPEC-0900 --auto" und "/api/pipeline/<id>" liefert status, log und report

  Scenario: Config-Migration
    Given config.yaml enthält task_routing.enabled true mit Schwelle 50 und llm.local_llm
    When ich "sdd upgrade" ausführe
    Then enthält config.yaml llm.profiles.lokal und by_complexity low und medium = lokal
    And task_routing und llm.local_llm sind auskommentiert
```

## 7. Edge Cases & Fehlerfälle

- `--session` mit einer unbekannten Rolle: Exit 2.
- Web-Route, während der Supervisor im Modus `session` wartet: `status` ist `paused`, das Log nennt
  `sdd pipeline decide`.
- `sdd upgrade` ohne `llm.local_llm`, aber mit `task_routing`: nur Auskommentieren, Hinweis.

## 8. Contracts (was wird garantiert)

| Contract-ID | Typ      | Was wird garantiert? |
|-------------|----------|----------------------|
| CON-XXXX    | behavior | Verweise, Entfernen, Config-Migration, Lifecycle, ARCH-05 |
| CON-XXXX    | behavior | Run-Optionen, `/sdd-implement`, Web-Route als Adapter, `sdd start --auto`, Action-Vorlage |

## 9. Tests (wie wird verifiziert)

| Test-ID  | Level       | Was prüft der Test? |
|----------|-------------|---------------------|
| TST-XXXX | acceptance  | Verweise, Migration, Entfernen, ARCH-05 |
| TST-XXXX | acceptance  | Run-Optionen, Web-Adapter mit Fake-LLM-Server, `sdd start --auto`, Skill- und Action-Text |

## 10. Offene Fragen

- [x] Belegung für `/sdd-implement`: Run-Option `--session` (entschieden 2026-09-26).
- [x] Web-Route: Adapter, Vertrag bleibt (entschieden 2026-09-26).
- [x] Architekturregel: Schicht `pipeline` + Facade, ARCH-05 (entschieden 2026-09-26).
- [x] Action: keyfrei über `claude-cli` geht im CI nicht; Key nur bei `provider: anthropic`.

## 11. Änderungshistorie

| Datum      | Version | Autor         | Änderung |
|------------|---------|---------------|----------|
| 2026-09-26 | 0.1.0   | Boris, Claude | Aus SPEC-0061 0.1.0 abgespalten (Review) |
| 2026-09-26 | 0.2.0   | Boris, Claude | Review: `--session`/`--steps`, Web-Adapter, `sdd start --auto`, ARCH-05, Migration |
