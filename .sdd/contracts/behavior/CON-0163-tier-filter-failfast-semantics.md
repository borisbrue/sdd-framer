---
id: CON-0163
project: PRJ-0001
title: "Tier-Filter und Fail-Fast-Semantik von sdd evaluate"
type: behavior
format: markdown
spec: SPEC-0042
version: 0.1.0
status: approved
artifact: "contracts/behavior/tier-filter-failfast-semantics.md"
tests: ["TST-0188", "TST-0191"]
---

# Contract: Tier-Filter und Fail-Fast-Semantik

> **Spec:** SPEC-0042 · **Typ:** Verhalten · **Status:** draft

## Zweck

Definiert das beobachtbare Verhalten von `sdd evaluate` bezüglich Tier-Filterung
und Fail-Fast-Übersprüngen — sowohl im Standard-Modus als auch mit `--tier`.

## Verhalten

### Standard-Modus (kein `--tier`)

Reihenfolge: critical → normal → edge-case.

| Situation                             | Verhalten                                                          |
|---------------------------------------|--------------------------------------------------------------------|
| critical schlägt fehl                | normal und edge-case werden übersprungen (status: skipped)         |
| critical besteht, normal schlägt fehl | edge-case wird übersprungen (status: skipped)                      |
| alle bestehen                         | alle ausgeführt, Exit 0                                            |

### `--tier critical`-Modus

| Situation                  | Verhalten                                            |
|----------------------------|------------------------------------------------------|
| critical schlägt fehl      | Exit 1; normal + edge-case werden **nicht** geladen  |
| critical besteht           | Exit 0; normal + edge-case werden **nicht** geladen  |
| keine critical-Holdouts    | Exit 0; Meldung "0 Holdouts für tier=critical gefunden" |

Analoges Verhalten für `--tier normal` und `--tier edge-case`.

### `--smoke`-Modus

```gherkin
Feature: Smoke-Test Selbsttest

  Scenario: Sortierung korrekt
    Given drei Mock-Holdouts: HOL-X (edge-case), HOL-Y (critical), HOL-Z (normal)
    When sdd evaluate --smoke ausgeführt wird
    Then werden sie in Reihenfolge HOL-Y → HOL-Z → HOL-X ausgeführt
    And Ausgabe enthält "✓ Tier-Sortierung korrekt"

  Scenario: Fail-Fast critical→normal
    Given HOL-Y (critical) schlägt fehl
    When sdd evaluate --smoke ausgeführt wird
    Then HOL-Z (normal) und HOL-X (edge-case) haben Status skipped
    And Ausgabe enthält "✓ Fail-Fast critical→normal korrekt"

  Scenario: Fail-Fast normal→edge-case
    Given HOL-Y (critical) besteht, HOL-Z (normal) schlägt fehl
    When sdd evaluate --smoke ausgeführt wird
    Then HOL-X (edge-case) hat Status skipped
    And Ausgabe enthält "✓ Fail-Fast normal→edge-case korrekt"

  Scenario: Alle bestehen
    Given alle drei Mock-Holdouts bestehen
    When sdd evaluate --smoke ausgeführt wird
    Then Exit-Code ist 0
    And Laufzeit < 2 s

  Scenario: Smoke-Test fehlschlägt
    Given die Tier-Sortierung ist falsch implementiert
    When sdd evaluate --smoke ausgeführt wird
    Then Exit-Code ist 1
    And Ausgabe enthält "✗ Tier-Sortierung"
```

## Invarianten

- `--smoke` macht keinen HTTP-Aufruf (kein `requests`, kein `httpx`)
- `--smoke` macht keinen LLM-Aufruf
- `--smoke` liest keine `.sdd/holdout/`-Dateien
- Laufzeit von `--smoke` < 2 s (rein lokale Berechnung + Mock-Objekte)
