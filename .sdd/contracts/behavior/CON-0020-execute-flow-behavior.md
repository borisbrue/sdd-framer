---
id: CON-0020
project: ""
title: "Execute Flow – UI-Verhalten und Status-Übergänge"
type: behavior
format: gherkin
spec: SPEC-0007
version: 0.3.0
status: active
artifact: "contracts/behavior/execute-flow-behavior.feature"
tests: ["TST-0025"]
---

# Contract: Execute Flow – UI-Verhalten und Status-Übergänge

> **Spec:** SPEC-0007 · **Typ:** Verhalten (Gherkin) · **Status:** draft

## Zweck

Definiert das beobachtbare Verhalten des Execute-Buttons, des
Pipeline-Status-Panels und der automatischen Status-Transition
von `approved` → `implemented`.

## Garantien

Die im Artifact (`contracts/behavior/execute-flow-behavior.feature`)
hinterlegten Szenarien sind **ausführbare Spezifikation**. Jedes
Szenario MUSS durch einen automatisierten Test abgedeckt sein.

## Invarianten

- **INV-01:** Der "Execute"-Button ist nur sichtbar wenn `status == approved`
  **und** `pipeline_phase == execute-unlocked` (CON-0025). `status == approved`
  ist notwendige, aber nicht hinreichende Bedingung — CON-0025 definiert die
  vollständige Execute-Gate-Bedingung.
- **INV-02:** Während ein Pipeline-Lauf für eine Spec aktiv ist, ist der
  Execute-Button dieser Spec deaktiviert (kein Doppel-Start möglich).
- **INV-03:** Nach `final_status in (labeled, merged)` wird die Spec-Datei
  automatisch auf `status: implemented` gesetzt.
- **INV-04:** Nach `final_status == failed` wird der Spec-Status nicht verändert.
- **INV-05:** `POST /api/orchestrate` gibt HTTP 422 zurück wenn die Spec nicht
  `status == approved` hat; gibt HTTP 409 zurück wenn `pipeline_phase !=
  execute-unlocked` (außer `--force` mit `override-reason`, siehe CON-0025).
- **INV-06:** Das Status-Panel stoppt das Polling automatisch sobald ein
  Endzustand erreicht ist (`labeled | merged | failed | dry_run`).

## Begriffe

| Begriff         | Definition                                                                     |
|-----------------|--------------------------------------------------------------------------------|
| Execute-Gate    | `status == approved` (notwendig) **und** `pipeline_phase == execute-unlocked` (hinreichend, CON-0025) sowie kein laufender Run für diese Spec-ID |
| Pipeline-Run    | Ein vollständiger Orchestrator-Zyklus ausgelöst durch POST /api/orchestrate   |
| run_id          | Eindeutige ID eines Pipeline-Runs: `{spec_id}-{unix_timestamp_ms}`            |
| Endzustand      | Einer der Werte: `labeled`, `merged`, `failed`, `dry_run`                     |
| Status-Panel    | UI-Komponente in SpecDetail, die den laufenden Pipeline-Fortschritt zeigt     |
