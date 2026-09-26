---
id: CON-0142
project: ""
title: "SchedulerCommand Protocol — apply-Semantik und DAG-Invarianz"
type: behavior
format: gherkin
spec: SPEC-0037
version: 0.1.0
status: deprecated
artifact: "tool/sdd_cli/dag_commands.py"
tests: ["TST-0163", "TST-0166"]
deprecated_reason: "mit SPEC-0037 abgelöst: Autopilot nie lauffähig; der Monitor liest seit SPEC-0058 das Pipeline-Protokoll"
---

# Contract: SchedulerCommand Protocol

> **Spec:** SPEC-0037 · **Typ:** Verhalten · **Status:** approved

## Zweck

Definiert die Protokoll-Garantien für `SchedulerCommand`-Objekte, die WebUI-
Nutzereingriffe (Pause, ForceRoute, Skip, Restart) als Commands kapseln (FR-04,
Pattern Command §3).

## Invarianten

- **INV-01:** `apply(scheduler)` ist idempotent — mehrfacher Aufruf mit demselben
  Command führt zum selben Ergebnis ohne Seiteneffekte.
- **INV-02:** `skip_task` wird abgelehnt (HTTP 422) wenn der Task noch offene
  Abhängigkeiten hat, die nicht `done` oder `skipped` sind — DAG-Invarianz.
- **INV-03:** `restart_task` ist nur für Tasks mit `status == "failed"` zulässig;
  bei anderen Stati wird der Command mit HTTP 422 abgelehnt (FR-04).
- **INV-04:** Unbekannte Command-Typen werden mit HTTP 422 abgelehnt.
- **INV-05:** `force_local` und `force_cloud` überschreiben das Routing für den
  nächsten Dispatch-Tick; das Override wird nach Completion des Tasks automatisch
  zurückgesetzt.
