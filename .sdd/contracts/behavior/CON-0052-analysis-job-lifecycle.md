---
id: CON-0052
project: PRJ-0001
title: "Analysis Job Lifecycle – Zustandsübergänge und Fehlerverhalten"
type: behavior
format: gherkin
spec: SPEC-0016
version: 0.1.0
status: draft
artifact: ""
tests: ["TST-0005"]
---

# Contract: Analysis Job Lifecycle

> **Spec:** SPEC-0016 · **Typ:** Verhalten (Gherkin) · **Status:** draft

## Zweck

Definiert das beobachtbare Verhalten des Analyse-Jobs vom Start bis zur
Persistierung oder zum Fehlerfall.

## Invarianten

- **INV-01:** Status-Übergänge sind nur in Vorwärtsrichtung erlaubt:
  `queued → running → complete` oder `queued → running → failed`.
- **INV-02:** Ein `complete`-Job schreibt genau eine JSON-Datei ins Repository.
- **INV-03:** Ein `failed`-Job schreibt keine JSON-Datei.
- **INV-04:** Ein Job der länger als 120 s im Status `running` bleibt,
  wird automatisch auf `failed` gesetzt mit `error: "Timeout"`.
- **INV-05:** Beim Prozessstart ist der JobStore leer (keine Persistenz).

## Gherkin-Szenarien

```gherkin
Feature: Analysis Job Lifecycle

  Background:
    Given der JobStore ist leer
    And das AnalysisRepository ist mit einem temporären Verzeichnis konfiguriert

  Scenario: Erfolgreicher Job-Durchlauf
    Given ein valider POST /analyze/start Request für "SPEC-0016"
    When der Endpunkt den Job erstellt
    Then antwortet er mit HTTP 202
    And die Response enthält ein "job_id" Feld (UUID4-Format)
    And die Response enthält "status": "queued"
    When der Background-Task die Analyse ausführt
    Then ändert sich der Job-Status zu "running"
    And schließlich zu "complete"
    And result_id ist nicht null
    And eine JSON-Datei existiert im Repository unter ".sdd/analyses/SPEC-0016/"

  Scenario: Status-Poll während Job läuft
    Given ein Job mit status "running" und job_id "abc"
    When GET /analyze/status/abc aufgerufen wird
    Then antwortet er mit HTTP 200
    And die Response enthält "status": "running"
    And "result_id" ist null

  Scenario: Status-Poll nach Fertigstellung
    Given ein Job mit status "complete", result_id "2026-05-16T12:00:00_abc12345"
    When GET /analyze/status/abc aufgerufen wird
    Then antwortet er mit HTTP 200
    And "status" ist "complete"
    And "result_id" ist "2026-05-16T12:00:00_abc12345"

  Scenario: Unbekannter job_id gibt 404
    Given kein Job mit job_id "unknown-id"
    When GET /analyze/status/unknown-id aufgerufen wird
    Then antwortet er mit HTTP 404

  Scenario: LLM-Fehler führt zu failed-Status
    Given der analyze()-Aufruf wirft eine RuntimeError-Exception
    When der Background-Task ausgeführt wird
    Then ist der Job-Status "failed"
    And error enthält die Exception-Message
    And keine JSON-Datei wurde ins Repository geschrieben

  Scenario: Timeout nach 120s führt zu failed-Status
    Given ein Job bleibt länger als 120s im Status "running"
    When der Timeout-Watchdog aktiv ist
    Then wird der Job-Status auf "failed" gesetzt
    And error enthält "Timeout"

  Scenario: Concurrent-Jobs-Limit (429)
    Given 5 aktive Jobs (status "queued" oder "running") für "SPEC-0016"
    When ein weiterer POST /analyze/start für "SPEC-0016" kommt
    Then antwortet er mit HTTP 429

  Scenario: TTL-Cleanup nach 24h
    Given ein Job mit updated_at älter als 24 Stunden
    When cleanup_expired() aufgerufen wird
    Then wird der Job aus dem JobStore entfernt
    And GET /analyze/status/{job_id} antwortet danach mit HTTP 404
```
