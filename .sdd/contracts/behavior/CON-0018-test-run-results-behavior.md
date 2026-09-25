---
id: CON-0018
project: ""                # PRJ-XXXX
title: "Test Run Results Behavior"
type: behavior
format: gherkin
spec: SPEC-0006
version: 0.1.0
status: draft
artifact: "contracts/behavior/test-run-results-behavior.feature"
tests: ["TST-0018"]
---

# Contract: Test Run Results Behavior

> **Spec:** SPEC-0006 · **Typ:** Verhalten (Gherkin) · **Status:** draft

## Zweck

<!-- Welches beobachtbare Verhalten wird hier festgeschrieben? -->

## Garantien

Die im Artifact (`contracts/behavior/test-run-results-behavior.feature`) hinterlegten Szenarien sind **ausführbare Spezifikation**.
Jedes Szenario MUSS durch einen automatisierten Test (z.B. Cucumber, behave, SpecFlow) abgedeckt sein.

## Invarianten (über alle Szenarien hinweg)

- **INV-01:** ...

## Begriffe

<!-- Domänensprache, die in den Szenarien verwendet wird -->

| Begriff   | Definition |
|-----------|------------|
| ...       | ...        |

## Erweiterung durch SPEC-0054

Die Szenarien dieses Contracts gelten **ohne** Testsonde unverändert. Mit Testsonde ersetzt die
Sonde den pytest-Runner, es gibt kein `runner: unsupported`, und Exit 2 steht zusätzlich für eine
ausgefallene Sonde oder eine ungültige `quality.yaml` (CON-0197 INV-05b).
