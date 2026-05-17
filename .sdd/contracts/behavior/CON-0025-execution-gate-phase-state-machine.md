---
id: CON-0025
project: PRJ-0001
title: "Execution Gate – Phase State Machine"
type: behavior
format: gherkin
spec: SPEC-0014
version: 0.1.0
status: draft
artifact: "contracts/behavior/execution-gate-phase-state-machine.feature"
tests: ["TST-0037"]
---

# Contract: Execution Gate – Phase State Machine

> **Spec:** SPEC-0014 · **Typ:** Verhalten (Gherkin) · **Status:** draft

## Zweck

Definiert die 8 obligatorischen Phasen, die eine SPEC durchlaufen muss, bevor
`sdd execute` freigegeben wird. Dieser Contract **erweitert** CON-0020 (Execute Flow):
CON-0020 INV-01 bleibt gültig (`status == approved` ist notwendige Bedingung),
wird hier jedoch um `pipeline_phase == execute-unlocked` als zusätzliche
hinreichende Bedingung ergänzt.

## Garantien

Die im Artifact hinterlegten Szenarien sind **ausführbare Spezifikation**.
Jedes Szenario MUSS durch einen automatisierten Test abgedeckt sein.

## Invarianten

- **INV-01:** `sdd execute` ist nur erlaubt wenn `status == approved` UND
  `pipeline_phase == execute-unlocked` (erweitert CON-0020 INV-01).
- **INV-02:** Phasenübergänge sind strikt sequenziell — Phase N kann nicht
  begonnen werden, wenn Phase N-1 nicht `result: ok` hat.
- **INV-03:** Jeder Phasenabschluss wird sofort in das Pipeline-JSON
  persistiert — ein CLI-Crash zwischen zwei Phasen verliert keinen Fortschritt.
- **INV-04:** Einzelne Phasen können wiederholt werden, ohne vorherige
  Phasen neu zu starten.
- **INV-05:** Ein `--force`-Override ohne `--override-reason` wird mit
  Exit-Code 1 abgelehnt; kein silentes Überspringen.
- **INV-06:** Jeder Override wird mit Zeitstempel und Begründung im
  Pipeline-JSON protokolliert.

## Phasenmodell

| Phase | Name                | Auslöser              | Exit-Kriterium |
|-------|---------------------|-----------------------|----------------|
| 1     | spec-draft          | Datei erstellt        | Pflichtfelder valide |
| 2     | spec-review         | `sdd spec review`     | 0 offene Critique-Items oder alle dismissed |
| 3     | contracts-proposed  | `sdd contract propose`| ≥1 Contract-Vorschlag |
| 4     | contracts-draft     | Dateien angelegt      | Alle vorgeschlagenen Contracts existieren |
| 5     | contracts-review    | `sdd contract review` | 0 offene Konflikte |
| 6     | tests-generated     | `sdd test generate`   | Testdateien syntaktisch valide |
| 7     | regression-ok       | `sdd test run`        | pass_threshold erfüllt |
| 8     | spec-approved       | `sdd spec approve`    | LLM-Konsistenzcheck grün |
| 9     | execute-unlocked    | Automatisch nach Ph.8 | — |

## Begriffe

| Begriff              | Definition |
|----------------------|------------|
| pipeline_phase       | Aktuell abgeschlossene Phase, gespeichert im Pipeline-JSON |
| execute-unlocked     | Terminalzustand: alle 8 Phasen bestanden, Execute freigegeben |
| Critique-Item        | LLM-Feedback-Einheit mit Abschnittsbezug, dismissbar durch Autor |
| Override             | Erzwungener Execute trotz unvollständiger Phasen, mit Begründungspflicht |
