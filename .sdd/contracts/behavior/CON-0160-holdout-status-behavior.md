---
id: CON-0160
project: ""
title: "Holdout-Status ContainerView Verhalten"
type: behavior
format: gherkin
spec: SPEC-0043
version: 0.1.0
status: approved
artifact: "contracts/behavior/CON-0160-holdout-status-behavior.feature"
tests: ["TST-0186"]
---

# Contract: Holdout-Status ContainerView Verhalten

> **Spec:** SPEC-0043 · **Typ:** Verhalten (Gherkin) · **Status:** draft

## Zweck

Garantiert das beobachtbare Verhalten des ContainerViews beim Anzeigen
von Holdout-Status-Badges und Szenario-Details. Deckt FR-02 und FR-03
aus SPEC-0043 ab.

## Garantien

Die im Artifact (`contracts/behavior/CON-0160-holdout-status-behavior.feature`)
hinterlegten Szenarien sind **ausführbare Spezifikation**.
Jedes Szenario MUSS durch einen automatisierten Test (behave / pytest-bdd)
abgedeckt sein.

## Invarianten (über alle Szenarien hinweg)

- **INV-01:** Der Badge zeigt immer einen Text-Label (nicht nur Farbe) – WCAG 2.1 AA
- **INV-02:** Nur der neueste Holdout-Lauf wird angezeigt
- **INV-03:** Die Anzeige ist rein lesend – keine Trigger-Aktionen im UI
- **INV-04:** Bei SSE-Verbindungsabbruch zeigt der Badge "unknown" mit Reconnect-Backoff

## Begriffe

| Begriff        | Definition                                                  |
|----------------|-------------------------------------------------------------|
| ContainerView  | UI-Ansicht einer einzelnen Spec im SDD Hub                  |
| Status-Badge   | Visuelles Element mit Text-Label: running/passed/failed/none |
| Holdout-Lauf   | Eine Evaluierungs-Session für eine Spec (neuester = aktiv)  |
| Szenario       | Ein Gherkin-Szenario innerhalb eines Holdout-Laufs          |
