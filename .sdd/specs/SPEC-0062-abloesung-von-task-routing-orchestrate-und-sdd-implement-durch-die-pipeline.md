---
id: SPEC-0062
title: "Ablösung von task-routing, orchestrate und sdd-implement durch die Pipeline"
type: feature
status: draft
owner: "Boris"
created: 2026-09-26
updated: 2026-09-26
version: 0.1.0
priority: medium
tags: [pipeline, refactoring, cleanup, skill]
depends_on: [SPEC-0061, SPEC-0058, SPEC-0059]
contracts: []
tests: []
---

# Ablösung von task-routing, orchestrate und sdd-implement durch die Pipeline

> **Status:** draft · **Owner:** Boris · **Version:** 0.1.0

## 1. Kontext & Motivation

Mit SPEC-0061 kann `sdd pipeline` alles, was die lebendigen alten Pfade leisten. Diese Spec stellt
die Einstiege um und entfernt die alten Pfade (aus SPEC-0061 0.1.0 abgespalten, Review 2026-09-26):

| Pfad | Zustand | Ersatz |
|------|---------|--------|
| `task_routing/` (924 Zeilen) mit `task-route`, `task-exec`, `task-loop` | aktiv, `/sdd-implement` ruft es auf | `by_complexity`, `--task`, `sdd pipeline run` |
| `sdd orchestrate`, `orchestrator.py`, Web-Route `orchestrate` | aktiv, Web-UI „Execute“ | `sdd pipeline run --auto` |
| CodeGen-Pfad (`get_code_gen_provider`, Schreiben in `openai_compat.py`) | nur von den beiden Pfaden oben genutzt | Rollen `test_author`/`implementer` |
| `/sdd-implement` (Repo-Kopie v0.9, Blueprint v0.7 auseinandergelaufen) | Claude implementiert, ruft `task-route`/`task-exec` | Belegung: test_author, implementer, supervisor im Modus `session` |
| GitHub-Action-Vorlage `sdd-orchestrate.yml` | ruft `sdd orchestrate` mit `ANTHROPIC_API_KEY` | `sdd pipeline run --auto` |

## 2. Zielsetzung

**Primärziel:** Es gibt genau einen Ausführungspfad, `sdd pipeline`. Alle Einstiege sind Belegungen
dieses Pfads.

**Erfolgskriterien (messbar):**
- [ ] `task_routing/`, `orchestrator.py` und der CodeGen-Pfad sind entfernt; die Testsuite ist grün.
- [ ] `task-route`, `task-exec`, `task-loop` und `orchestrate` sind Verweise (Hinweis, Exit 1).
- [ ] `/sdd-implement`, `sdd pipeline run --auto` und die Web-UI schreiben in dasselbe Run-Protokoll.
- [ ] Die Baseline hat keinen Eintrag mehr mit `fixed_by: SPEC-0061` oder `SPEC-0062`.

**Nicht-Ziele (explizit):**
- Keine neuen Pipeline-Fähigkeiten (SPEC-0061).
- Keine Anpassung der VS-Code-Extension.

## 4. Funktionale Anforderungen (Entwurf)

- **FR-01:** `/sdd-implement` läuft über `sdd pipeline run` mit `test_author`, `implementer` und
  `supervisor` im Modus `session`; `decomposer` und `reviewer` aus `llm.roles`. Repo-Kopie und
  Blueprint des Skills sind danach identisch.
- **FR-02:** `task-route`, `task-exec`, `task-loop` und `orchestrate` werden Verweise (Hinweis,
  Exit 1, keine Ausführung).
- **FR-03:** Die Web-Route `POST /api/orchestrate` startet `sdd pipeline run --auto`; die
  Lese-Routen zeigen Pipeline-Runs.
- **FR-04:** `task_routing/` und `orchestrator.py` werden entfernt; `sdd upgrade` migriert
  `task_routing` und `llm.local_llm` nach `llm.profiles` und
  `llm.roles.implementer.by_complexity` (Schwelle → Stufen) und kommentiert die alten Blöcke aus.
- **FR-05:** Der CodeGen-Pfad (`get_code_gen_provider`, `CodeGenProvider`-Implementierungen) wird
  entfernt; der ARCH-01-Eintrag für `openai_compat.py` entfällt.
- **FR-06:** Die GitHub-Action-Vorlage ruft `sdd pipeline run --auto` und läuft keyfrei, wo möglich.
- **FR-07:** SPEC-0045 wird über `sdd spec deprecate` abgelöst; SPEC-0004 bekommt den Hinweis auf
  die Pipeline.
- **FR-08:** Eine Regel in `.sdd/architecture.yaml` sichert ab, dass keine Schicht außerhalb von
  `pipeline` Tasks ausführt (konkrete Form im Review, DIP-Befund aus SPEC-0061).

## 10. Offene Fragen

- [ ] Wie lässt sich „Task-Arbeit nur in der Pipeline“ maschinell prüfen (DIP-Befund)?
- [ ] Welche Teile der GitHub-Action können keyfrei laufen?

## 11. Änderungshistorie

| Datum      | Version | Autor         | Änderung |
|------------|---------|---------------|----------|
| 2026-09-26 | 0.1.0   | Boris, Claude | Aus SPEC-0061 0.1.0 abgespalten (Review) |
