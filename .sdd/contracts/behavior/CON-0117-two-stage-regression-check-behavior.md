---
id: CON-0117
project: ""                # PRJ-XXXX
title: "Two-Stage Regression Check Behavior"
type: behavior
format: gherkin
spec: SPEC-0030
version: 0.1.0
status: approved
artifact: ".sdd/contracts/behavior/two-stage-regression-check-behavior.feature"
tests: ["TST-0136"]
---

# Contract: Two-Stage Regression Check Behavior

> **Spec:** SPEC-0030 · **Typ:** Verhalten (Gherkin) · **Status:** draft

## Zweck

Beschreibt das beobachtbare Verhalten von `sdd regression-check SPEC-XXXX`:
- Stufe 1 (regelbasiert) läuft immer zuerst; Stufe 2 (LLM) schließt sich automatisch an (FR-01)
- Exit-Code-Semantik bei error/warning/info-Befunden (FR-05)
- Graceful Degradation wenn das LLM nicht erreichbar ist (FR-06)

## Garantien

Die im Artifact (`.sdd/contracts/behavior/two-stage-regression-check-behavior.feature`) hinterlegten Szenarien sind **ausführbare Spezifikation**.
Jedes Szenario MUSS durch einen automatisierten Test (behave oder pytest-bdd) abgedeckt sein.

## Invarianten (über alle Szenarien hinweg)

- **INV-01:** Stufe 2 (LLM) läuft immer nach Stufe 1, nie davor und nie ohne Stufe 1.
- **INV-02:** Exit-Code 1 wenn mindestens ein Befund mit `severity: error` vorliegt (unabhängig ob `[rule]` oder `[llm]`); Exit-Code 0 bei ausschließlich `warning`/`info`.
- **INV-03:** Bei jeglichem LLM-Fehler (API-Timeout, ungültiger Key, Rate-Limit, Netzwerkfehler) wird Stufe 2 übersprungen mit der Warnung `[llm] ⚠ LLM-Check übersprungen (kein API-Zugang)`; Stufe-1-Ergebnisse werden vollständig ausgegeben. Ein LLM-Fehler erhöht nie den Exit-Code.
- **INV-04:** Specs im Status `draft` werden nie als Vergleichsbasis herangezogen — nur `implemented` und `in-progress`.

## Begriffe

| Begriff  | Definition |
|----------|------------|
| Stufe 1  | Regelbasierter, deterministischer Check (Endpoint-, Lifecycle-, Schema-Konflikte) |
| Stufe 2  | LLM-basierter Semantik-Check (inhaltliche Überschneidungen, Redundanzen) |
| Befund   | Ein einzelner gemeldeter Konflikt mit spec_id, section, severity und description |
| Degradation | Stufe 2 wird mit Warnung übersprungen wenn LLM nicht erreichbar ist |
