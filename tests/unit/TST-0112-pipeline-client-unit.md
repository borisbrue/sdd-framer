---
id: TST-0112
project: PRJ-0001
title: "PipelineClient – HTTP-Requests, Polling-Logik, Abort"
level: unit
spec: SPEC-0017
contract: CON-0055
status: planned
framework: vitest
artifact: "vscode-extension/src/__tests__/pipeline.test.ts"
tags: ["vscode", "pipeline", "http", "polling"]
---

# Test: PipelineClient – HTTP-Requests, Polling-Logik, Abort

> **Level:** unit · **Spec:** SPEC-0017 · **Contract:** CON-0055 · **Status:** planned

## Was wird geprüft?

- `orchestrate(specId, opts)` sendet korrekt `POST /api/orchestrate`
- `getPipelineRun(runId)` sendet `GET /api/pipeline/{run_id}`
- `getActivePipeline(specId)` sendet `GET /api/pipeline/active?spec_id=X`
- `abortPipeline(runId)` sendet `POST /api/pipeline/{run_id}/abort`
- Polling stoppt bei terminalem Status (`labeled`, `merged`, `failed`, `aborted`)
- Polling läuft weiter solange Status `running`
- HTTP-Fehler werden als Exception weitergeleitet

## Ablauf

### TC-01: orchestrate() – korrekter Request

1. Mock `fetch` → gibt `{ run_id: "RUN-001", status: "running" }` zurück
2. Rufe `orchestrate("SPEC-0007", {})` auf
3. Prüfe: `fetch` aufgerufen mit `POST`, URL enthält `/api/orchestrate`
4. Prüfe: Body enthält `{ spec_id: "SPEC-0007" }`

### TC-02: getPipelineRun() – korrekter Endpunkt

1. Mock `fetch` → gibt PipelineRunState zurück
2. Rufe `getPipelineRun("RUN-001")` auf
3. Prüfe: URL ist `…/api/pipeline/RUN-001`

### TC-03: getActivePipeline() – Query-Parameter

1. Mock `fetch`
2. Rufe `getActivePipeline("SPEC-0007")` auf
3. Prüfe: URL enthält `spec_id=SPEC-0007`

### TC-04: abortPipeline() – POST an Abort-Endpunkt

1. Mock `fetch`
2. Rufe `abortPipeline("RUN-001")` auf
3. Prüfe: Method `POST`, URL enthält `/api/pipeline/RUN-001/abort`

### TC-05: Polling – stoppt bei terminalem Status

1. Mock `getPipelineRun`: 1. Aufruf → `running`, 2. Aufruf → `labeled`
2. Starte Polling mit Interval 10ms
3. Prüfe: Polling-Callback wird zweimal aufgerufen, dann stoppt Polling

### TC-06: Polling – kein Idle-Polling nach Terminal

1. Wie TC-05, aber warte 3× Interval nach Terminal
2. Prüfe: `getPipelineRun` wird nicht öfter als 2× aufgerufen

### TC-07: HTTP-Fehler propagation

1. Mock `fetch` → wirft `Error("Network error")`
2. Prüfe: `orchestrate()` wirft ebenfalls eine Exception

## Erwartetes Ergebnis

Alle 7 Test-Cases grün. Kein echter HTTP-Call wird abgesetzt (fetch vollständig gemockt).
