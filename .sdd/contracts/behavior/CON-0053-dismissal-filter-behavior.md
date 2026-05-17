---
id: CON-0053
project: PRJ-0001
title: "Dismissal Filter – Kontext-Pruning bei Folge-Analysen"
type: behavior
format: gherkin
spec: SPEC-0016
version: 0.1.0
status: draft
artifact: ""
tests: ["TST-0067"]
---

# Contract: Dismissal Filter Behavior

> **Spec:** SPEC-0016 · **Typ:** Verhalten (Gherkin) · **Status:** draft

## Zweck

Definiert das Verhalten des `DismissalFilter`, der abgehakte Items aus dem
LLM-Prompt einer Folge-Analyse entfernt, und das Persistierungsverhalten
des `PATCH /dismiss`-Endpunkts.

## Invarianten

- **INV-01:** Ein dismisster Item verbleibt in der `dismissed_ids`-Liste der gespeicherten
  Analyse; er wird nicht gelöscht.
- **INV-02:** Beim Folge-Analyse-Start werden `dismissed_ids` an das Backend übergeben.
  Das Backend übergibt sie dem `DismissalFilter` vor dem LLM-Aufruf.
- **INV-03:** Der Filter entfernt ausschließlich `questions`, deren `id` in
  `dismissed_ids` enthalten ist. `issues` und `suggestions` haben keine IDs und
  werden in v0.1.0 nicht gefiltert.
- **INV-04:** Unbekannte IDs in `dismissed_ids` werden still ignoriert (kein Fehler).
- **INV-05:** `dismissed: false` in einem PATCH-Request reaktiviert ein Item
  (entfernt die ID aus `dismissed_ids`).

## Gherkin-Szenarien

```gherkin
Feature: Dismissal Filter Behavior

  Background:
    Given das AnalysisRepository hat eine gespeicherte Analyse "2026-05-16T12:00:00_abc12345"
    And die Analyse enthält questions mit IDs ["q-001", "q-002", "q-003"]
    And dismissed_ids ist []

  Scenario: Item abhaken speichert ID persistent
    When PATCH /analyses/2026-05-16T12:00:00_abc12345/dismiss mit { "item_id": "q-001", "dismissed": true }
    Then antwortet er mit HTTP 200
    And die Response enthält "dismissed_ids": ["q-001"]
    And die JSON-Datei auf Disk enthält "dismissed_ids": ["q-001"]

  Scenario: Zweites Item abhaken fügt zur Liste hinzu
    Given dismissed_ids ist ["q-001"]
    When PATCH /dismiss mit { "item_id": "q-002", "dismissed": true }
    Then "dismissed_ids" ist ["q-001", "q-002"]

  Scenario: Item reaktivieren entfernt aus Liste
    Given dismissed_ids ist ["q-001", "q-002"]
    When PATCH /dismiss mit { "item_id": "q-001", "dismissed": false }
    Then "dismissed_ids" ist ["q-002"]

  Scenario: Unbekannter result_id gibt 404
    When PATCH /analyses/nonexistent/dismiss mit { "item_id": "q-001", "dismissed": true }
    Then antwortet er mit HTTP 404

  Scenario: Leere item_id gibt 400
    When PATCH /dismiss mit { "item_id": "", "dismissed": true }
    Then antwortet er mit HTTP 400

  Scenario: Dismissed IDs werden beim Folge-Analyse-Prompt gefiltert
    Given dismissed_ids ist ["q-001"]
    And eine neue Analyse wird gestartet mit dismissed_ids ["q-001"]
    When der DismissalFilter den Prompt aufbaut
    Then enthält der Prompt keine Frage mit id "q-001"
    And die Fragen "q-002" und "q-003" sind im Prompt enthalten

  Scenario: Unbekannte dismissed_id wird still ignoriert
    Given dismissed_ids ist ["unknown-id-999"]
    When der DismissalFilter den Prompt aufbaut
    Then wirft der Filter keinen Fehler
    And alle bekannten Questions sind im Prompt enthalten

  Scenario: Idempotentes Abhaken (doppeltes PATCH)
    Given dismissed_ids ist ["q-001"]
    When PATCH /dismiss mit { "item_id": "q-001", "dismissed": true } erneut gesendet
    Then antwortet er mit HTTP 200
    And "dismissed_ids" ist weiterhin ["q-001"] (keine Duplikate)
```
