---
id: CON-0143
project: ""
title: "AutopilotStateMachine — Transitionen und Iterationszähler"
type: behavior
format: gherkin
spec: SPEC-0037
version: 0.1.0
status: approved
artifact: "tool/sdd_cli/autopilot.py"
tests: ["TST-0164"]
---

# Contract: AutopilotStateMachine

> **Spec:** SPEC-0037 · **Typ:** Verhalten · **Status:** approved

## Zweck

Definiert die deterministischen Zustandsübergänge des Autopiloten
(`sdd implement --auto`) sowie den Iterationszähler- und Fortschritts-Mechanismus
(FR-06–FR-10, Pattern State §3).

## Zustände

`idle → decomposing → implementing → testing → reviewing → finalizing → done`

Fehlerzustände: `fix_loop`, `escalated`

## Invarianten

- **INV-01:** Transitionen sind deterministisch — gleicher Zustand + gleicher
  Exit-Code führt immer zur selben Folge-Transition.
- **INV-02:** `fix_loop` inkrementiert `iteration_count` bei jeder Iteration.
  Wenn `iteration_count >= max_fix_iterations` UND kein Fortschritt erkannt:
  Transition nach `escalated`.
- **INV-03:** Fortschritt gilt als erkannt wenn mindestens ein vorher roter Test
  jetzt grün ist ODER ein Review-Finding behoben wurde.
- **INV-04:** `escalated` verbleibt im Zustand bis ein expliziter `SchedulerCommand`
  (retry / skip / abort) aus der WebUI oder dem Terminal empfangen wird.
- **INV-05:** Ist `autopilot.automated_gate_approval: false` (Default), stoppt
  die Maschine vor jedem SPEC-0014-Gate und wartet auf manuelle Bestätigung —
  kein autonomes Durchlaufen ohne Opt-in.
