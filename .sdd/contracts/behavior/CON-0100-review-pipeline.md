---
id: CON-0100
title: "ReviewPipeline – Automatische Prüfung und Retry-Logik"
type: behavior
format: gherkin
spec: SPEC-0026
version: 0.1.0
status: draft
artifact: "contracts/behavior/review-pipeline.feature"
tests:
- TST-0119
---

# Contract: ReviewPipeline – Automatische Prüfung und Retry-Logik

> **Spec:** SPEC-0026 · **Typ:** Verhalten (Gherkin) · **Status:** draft

## Zweck

Legt fest, wie das Ergebnis eines abgeschlossenen Tasks automatisch geprüft
wird und was bei positiver bzw. negativer Prüfung passiert (FR-09/10/11).
Die Pipeline ist eine Chain of Responsibility: Jeder Schritt kann die Kette
abbrechen und einen Retry auslösen.

## Garantien

- Die Pipeline besteht aus drei Stufen in fixer Reihenfolge:
  1. **Syntax-Check** (Linting, Type-Check): schnell, kein LLM
  2. **Unit-Tests**: führt vorhandene Tests aus
  3. **Claude-Code-Review**: Claude bewertet Korrektheit, Stil, SOLID-Einhaltung
- Jede Stufe emittiert `passed` oder `failed(reason)`.
- Bei `failed`: `error_context` wird um `reason` ergänzt, `retry_count` wird erhöht.
- Bei `retry_count == 3` und erneutem Fehler: Task wird `blocked`.
- Bei `passed` aller drei Stufen: Task wird `committed` mit Git-Commit auf Spec-Branch.

## Invarianten

- **INV-01:** Stufen werden immer in der Reihenfolge Syntax → Tests → Review ausgeführt.
- **INV-02:** `error_context` wächst monoton (Einträge werden nie gelöscht).
- **INV-03:** Ein `committed` Task hat exakt einen Git-Commit-Hash.
- **INV-04:** Retries erhalten den vollständigen `error_context` aller vorherigen Versuche als Kontext.

## Szenarien (Gherkin)

```gherkin
Feature: ReviewPipeline

  Scenario: Alle Stufen bestehen – Task wird committed
    Given Task T1 mit einem vollständigen LLM-Ergebnis
    When review_pipeline.run(T1) aufgerufen wird
    And Syntax-Check: passed
    And Unit-Tests: passed
    And Claude-Review: passed
    Then T1.status == "committed"
    And T1.commit_hash ist gesetzt (INV-03)

  Scenario: Syntax-Check schlägt fehl – Retry
    Given Task T1 mit retry_count=0
    When Syntax-Check für T1 schlägt fehl mit "TypeError: line 42"
    Then T1.error_context == ["TypeError: line 42"]
    And T1.retry_count == 1
    And T1.status == "retrying"
    And Unit-Tests und Claude-Review werden nicht ausgeführt (INV-01)

  Scenario: Dritter Fehlversuch – Task wird blocked
    Given Task T1 mit retry_count=2
    When Syntax-Check erneut fehlschlägt
    Then T1.retry_count == 3
    And T1.status == "blocked"
    And Entwickler wird benachrichtigt

  Scenario: Retry erhält vollen Fehlerkontext
    Given Task T1 mit error_context=["Fehler 1", "Fehler 2"]
    When T1 dem LLM für Retry übergeben wird
    Then enthält der LLM-Prompt beide vorherigen Fehlermeldungen (INV-04)

  Scenario: Claude-Review schlägt fehl, Syntax und Tests OK
    Given Task T1 mit retry_count=1
    When Syntax: passed, Tests: passed, Claude-Review: failed("SOLID-Verletzung")
    Then T1.error_context enthält "SOLID-Verletzung"
    And T1.retry_count == 2
    And T1.status == "retrying"
```

## Begriffe

| Begriff | Definition |
|---|---|
| error_context | Akkumulierte Fehlermeldungen aus allen bisherigen Retry-Versuchen |
| Blocked | Task nach 3 Fehlversuchen – erfordert manuellen Eingriff |
