---
id: CON-0211
title: "Pipeline-Monitor und Web-Routen"
type: behavior
format: gherkin
spec: SPEC-0058
version: 0.2.0
status: approved
artifact: ".sdd/contracts/behavior/pipeline-monitor-und-web-routen.feature"
tests: ["TST-0240"]
---

# Contract: Pipeline-Monitor und Web-Routen

> **Spec:** SPEC-0058 · **Typ:** Verhalten (Gherkin) · **Status:** approved

## Zweck

Legt die Leseschnittstelle für Pipeline-Runs fest (`sdd_cli.pipeline.monitor`), das
Verhalten der Monitor-Routen der Web-UI und der Web-Routen `implement`/`evaluate` (SPEC-0058 FR-05
bis FR-07). Die Web-Schicht liest Runs nur über diese Schnittstelle (ADR-0003).

## Garantien

Die Szenarien im Artifact (`.sdd/contracts/behavior/pipeline-monitor-und-web-routen.feature`) sind **ausführbare Spezifikation**. Jedes Szenario MUSS durch
einen automatisierten Test (pytest) abgedeckt sein.

## Invarianten

- **INV-01:** `monitor.list_runs(root)` liefert je Run `run_id`, `spec_id`, `status`,
  `started_at` (Unix-Zeit), neuester zuerst. Status-Abbildung aus `state.json`: `running` →
  `running`, `awaiting_supervisor` → `paused`, `completed` → `done`, `halted`/`failed` → `failed`.
- **INV-02:** `monitor.task_events(root, run_id, offset)` liefert `(ereignisse, neuer_offset)`. Nur
  Ereignisse mit `task_id` werden abgebildet: Transitionen nach `pending` → `pending`, nach
  `done` → `done`, nach `halted` → `failed`, alle übrigen → `running`; `role_call` und
  `write_rejected` → `running`. `agent` ist `cloud` für die Provider `claude-cli`/`anthropic`,
  `local` für andere, `none` ohne Provider. `details` nennt Rolle, Ergebnis bzw. Übergang.
- **INV-03:** Der Offset ist die Anzahl gelesener Zeilen von `events.jsonl`; `events.jsonl` wird nur
  angehängt (CON-0202 INV-04), daher liefert ein erneutes Lesen mit dem Offset genau die neuen
  Ereignisse.
- **INV-04:** Die Routen `GET /api/orchestrate/runs` und `GET /api/orchestrate/stream/{run_id}`
  behalten ihre Antwortformate (Liste wie bisher, SSE mit `data: <DagEvent-JSON>`). Der Stream
  prüft mindestens alle 2 s auf neue Ereignisse und endet, wenn der Run nicht mehr `running` ist
  und alle Ereignisse gesendet sind. Ein unbekannter Run liefert 404.
- **INV-05:** `POST /api/orchestrate/command/{run_id}` antwortet mit 410 und nennt
  `sdd pipeline decide`.
- **INV-06:** `sdd pipeline status RUN --json` gibt `run_id`, `status`, `phase`, `tasks` und
  `pending_request` (oder `null`) aus; Exit-Codes wie CON-0205.
- **INV-07:** `POST /api/specs/{id}/implement` und `/evaluate` behalten Antwortformat
  (`{"ok", "output"}`) und Log-Stream; sie rufen `sdd pipeline run` bzw. `sdd holdout run` auf,
  nie die entfernten Befehle `sdd implement`/`sdd evaluate`.
- **INV-08 (Abgrenzung):** Die Routen aus SPEC-0007 (`POST /api/orchestrate`,
  `GET /api/pipeline/{run_id}`, `/api/pipeline/active`, `/abort`) und die Run-Ablage von
  `sdd orchestrate` bleiben bis SPEC-0061 unverändert. `/api/orchestrate/runs` listet ausschließlich
  Runs von `sdd pipeline run` (`.sdd/runs/`). Der Status `skipped` wird von der Abbildung nicht
  erzeugt, bleibt aber im Format erlaubt.
