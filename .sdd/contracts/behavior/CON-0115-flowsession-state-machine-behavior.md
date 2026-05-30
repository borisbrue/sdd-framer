---
id: CON-0115
project: ""                # PRJ-XXXX
title: "FlowSession State Machine Behavior"
type: behavior
format: gherkin
spec: SPEC-0032
version: 0.1.0
status: active
artifact: ".sdd/contracts/behavior/flowsession-state-machine-behavior.feature"
tests: ["TST-0134"]
---

# Contract: FlowSession State Machine Behavior

> **Spec:** SPEC-0032 · **Typ:** Verhalten (Gherkin) · **Status:** draft

## Zweck

Beschreibt das beobachtbare Verhalten der `FlowSession` State Machine (SPEC-0032 §3):
- Zustandsübergänge zwischen `awaiting_input`, `awaiting_decision`, `running`, `done`, `failed`
- Decision-Point-Verhalten: Pause, Push-Notification, Ja/Nein-Eingabe, Fortsetzung (FR-05)
- PWA-Reconnect nach App-Neustart (FR-06)
- Delegation an SPEC-0016-JobStore (review) und SPEC-0007-Orchestrator (implement)

## Garantien

Die im Artifact (`.sdd/contracts/behavior/flowsession-state-machine-behavior.feature`) hinterlegten Szenarien sind **ausführbare Spezifikation**.
Jedes Szenario MUSS durch einen automatisierten Test (behave oder pytest-bdd) abgedeckt sein.

## Invarianten (über alle Szenarien hinweg)

- **INV-01:** Eine Session im State `done` oder `failed` akzeptiert keine weiteren Replies (HTTP 409).
- **INV-02:** Ein Decision Point (`awaiting_decision`) akzeptiert nur `"ja"` oder `"nein"` als Antwort; jede andere Eingabe gibt HTTP 422 zurück.
- **INV-03:** Nach Session-TTL-Ablauf gibt GET /api/agent/flow/{session_id} HTTP 404 zurück — kein automatischer Neustart.
- **INV-04:** Eine Flow-Session erstellt niemals einen eigenen Job-Store; sie referenziert immer den Job-Store des jeweiligen Subsystems (SPEC-0016 oder SPEC-0007).

## Begriffe

| Begriff | Definition |
|---|---|
| FlowSession | Server-seitiger Zustand eines geführten Flows mit Schritten, Antworten und aktuellem State |
| Decision Point | Schritt im Flow, der explizite Nutzerbestätigung (ja/nein) erfordert, bevor fortgefahren wird |
| Delegation | AgentFlowFacade übergibt Kontrolle an ein bestehendes Subsystem (SPEC-0005/0007/0016) |
| TTL | Time-to-Live einer Session; nach Ablauf wird der State gelöscht (kein Persist) |
