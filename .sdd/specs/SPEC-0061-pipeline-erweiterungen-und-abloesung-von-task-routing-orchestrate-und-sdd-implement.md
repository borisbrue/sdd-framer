---
id: SPEC-0061
title: "Pipeline-Erweiterungen und Ablösung von task-routing, orchestrate und sdd-implement"
type: feature           # feature | bug-fix
status: draft           # draft | review | approved | implemented | deprecated
owner: "Boris"
created: 2026-09-26
updated: 2026-09-26
version: 0.1.0
priority: medium
tags: [pipeline, refactoring, session, routing]
depends_on: [SPEC-0053, SPEC-0058, SPEC-0059]
contracts: []           # z.B. ["CON-0001"] – MUSS mindestens einen Eintrag enthalten
tests: []               # z.B. ["TST-0001"] – MUSS mindestens einen Eintrag enthalten
---

# Pipeline-Erweiterungen und Ablösung von task-routing, orchestrate und sdd-implement

> **Status:** draft · **Owner:** Boris · **Version:** 0.1.0

## 1. Kontext & Motivation

Beim Review von SPEC-0058 (2026-09-26) wurde die Konsolidierung geteilt. SPEC-0058 baut ab, was ohne
Funktionsverlust wegfallen kann. Diese Spec übernimmt die lebendigen Pfade, für die die Pipeline aus
SPEC-0053 erst neue Fähigkeiten braucht:

| Pfad | Zustand | Braucht in der Pipeline |
|------|---------|-------------------------|
| `task_routing/` mit `task-route`, `task-exec`, `task-loop` (924 Zeilen) | aktiv (`task_routing.enabled: true`), `/sdd-implement` ruft es auf | Routing nach Komplexität (`by_complexity`), Einzeltask (`--task`) |
| `/sdd-implement` | Claude implementiert im Dialog | Arbeitsrollen im Modus `session` |
| `sdd orchestrate` und Web-Route `orchestrate` | Code in einem Schritt, PR, Holdout-Gate, Retry, Auto-Merge | Abschluss-Schritte (`--auto`) |

Dazu kommen offene Punkte aus SPEC-0053 (Flag `allow_supervisor_implementation` für den Task-Loop,
Lint- und Architektur-Gates pro Task) und der ARCH-01-Eintrag des CodeGen-Pfads in der Baseline.

## 2. Zielsetzung

**Primärziel:** Nach dieser Spec gibt es genau einen Ausführungspfad, `sdd pipeline`. `/sdd-implement`,
`/sdd-supervise`, die Dark Factory und die Web-UI sind Belegungen dieses Pfads.

**Erfolgskriterien (messbar):**
- [ ] Kein Modul außerhalb von `tool/sdd_cli/pipeline/` enthält Retry-, Routing- oder
      Eskalationslogik für Tasks; eine Regel in `.sdd/architecture.yaml` sichert das ab.
- [ ] `task_routing/` ist entfernt; `task-route`, `task-exec`, `task-loop` und `orchestrate` sind
      Verweise (Hinweis, Exit 1).
- [ ] `/sdd-implement`, `sdd pipeline run --auto` und die Web-UI schreiben in dasselbe Run-Protokoll.
- [ ] Die Baseline hat keine Einträge mehr mit `fixed_by: SPEC-0061`.

**Nicht-Ziele (explizit):**
- Die Holdout-Evaluation selbst bleibt unverändert und wird nur als Abschluss-Gate eingebunden.
- Keine Anpassung der VS-Code-Extension.

## 3. Architektur & Design Patterns

Aus dem Review von SPEC-0058 übernommen (angenommen 2026-09-26):
- **Strategy:** Rollenbelegung je Task, `by_complexity` wählt die Strategie nach Komplexität.
- **Command:** Anfrage und Bestätigung einer Arbeitsrolle im Modus `session` nutzen dieselbe
  Command-Struktur wie die Supervisor-Entscheidungen (SPEC-0053 FR-08), aber einen eigenen Befehl
  (ISP-Befund: nicht `decide`).
- **Adapter:** Verweise alter Befehle und Config-Migration.

## 4. Funktionale Anforderungen (Entwurf, aus SPEC-0058 0.1.0)

- **FR-01:** Jede Arbeitsrolle akzeptiert `mode: session`. Statt eines LLM-Aufrufs wird eine Anfrage
  persistiert (Task, Kontext, erlaubte Pfade laut PathPolicy); die Session schreibt die Dateien und
  bestätigt mit einem eigenen Befehl (z. B. `sdd pipeline done RUN_ID TASK_ID`). Danach wertet die
  Pipeline die Gates aus.
- **FR-02:** `llm.roles.<rolle>.by_complexity` ordnet `low|medium|high` je ein Modellprofil zu.
- **FR-03:** `sdd pipeline run --task ID` bearbeitet einen einzelnen Task einer vorhandenen Zerlegung.
- **FR-04:** `sdd pipeline run --auto` aktiviert die Abschluss-Schritte Finalize (PR), Holdout-Gate
  mit Retry-Kontext und Auto-Merge nach Autonomie-Level. Die Schritte sind einzeln konfigurierbar
  (OCP-Befund).
- **FR-05:** `/sdd-implement` läuft über `sdd pipeline run` mit `test_author` und `implementer` im
  Modus `session`.
- **FR-06:** `task-route`, `task-exec`, `task-loop` und `orchestrate` werden Verweise (Hinweis,
  Exit 1); die Web-Route `orchestrate` startet die Pipeline mit `--auto`.
- **FR-07:** `task_routing/` wird entfernt; `sdd upgrade` migriert `task_routing` und `llm.local_llm`
  nach `llm.roles.implementer.by_complexity`.
- **FR-08:** Der CodeGen-Pfad (`get_code_gen_provider`, Schreiben in `openai_compat.py`) wird durch
  die Pipeline abgelöst; ARCH-01-Eintrag in der Baseline entfällt.
- **FR-09:** Lint- und Architektur-Gates aus SPEC-0054 laufen nach jedem Task (Rest aus SPEC-0053).
- **FR-10:** SPEC-0045 wird `deprecated`; SPEC-0004 bekommt den Hinweis auf die Pipeline.
- **FR-11:** Regel in `.sdd/architecture.yaml`: Provider-Aufrufe für Task-Arbeit nur unter
  `tool/sdd_cli/pipeline/**`.

## 5. Nicht-funktionale Anforderungen

| Kategorie   | Anforderung |
|-------------|-------------|
| Migration   | Verweise bleiben mindestens zwei Minor-Versionen bestehen. |
| Keyfreiheit | Kein Pfad setzt `ANTHROPIC_API_KEY` oder `ANTHROPIC_BASE_URL`. |

## 6. Akzeptanzkriterien (Gherkin)

Folgen im Review.

## 7. Edge Cases & Fehlerfälle

- Ein Session-Task wird nie bestätigt: `sdd pipeline status` zeigt `awaiting_session`; `--resume`
  setzt dort fort.
- Offene Runs aus `task-loop` beim Upgrade werden nicht migriert, sondern gemeldet.

## 8. Contracts (was wird garantiert)

Folgen im Review.

## 9. Tests (wie wird verifiziert)

Folgen im Review.

## 10. Offene Fragen

- [ ] Wie wird `session` für Arbeitsrollen bestätigt (eigener Befehl, Name)?
- [ ] Welche Abschluss-Schritte gehören zu `--auto`, welche sind einzeln schaltbar?

## 11. Änderungshistorie

| Datum      | Version | Autor         | Änderung |
|------------|---------|---------------|----------|
| 2026-09-26 | 0.1.0   | Boris, Claude | Aus SPEC-0058 0.1.0 abgespalten (Review) |
