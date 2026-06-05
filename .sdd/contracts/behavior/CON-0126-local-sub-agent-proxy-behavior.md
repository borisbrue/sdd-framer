---
id: CON-0126
project: ""
title: "LocalSubAgentProxy – Ausführungs- und Fehler-Eskalations-Contract"
type: behavior
format: gherkin
spec: SPEC-0036
version: 0.1.0
status: draft
artifact: ".sdd/contracts/behavior/local-sub-agent-proxy-behavior.feature"
tests: ["TST-0148"]
---

# Contract: LocalSubAgentProxy – Ausführungs- und Fehler-Eskalations-Contract

> **Spec:** SPEC-0036 · **Typ:** Verhalten (Gherkin) · **Status:** draft

## Geltungsbereich

Dieser Contract gilt für `LocalSubAgentProxy.execute()` und die Fehler-Eskalationslogik
des `DagScheduler` (FR-04, FR-09). Komplementär zu CON-0122 (SPEC-0035), das den
Cloud-Sub-Agenten beschreibt.

## Invarianten

- **INV-01:** `LocalSubAgentProxy.execute()` setzt immer `ANTHROPIC_BASE_URL` und
  `ANTHROPIC_API_KEY` als Subprocess-Env-Variablen — nie als Prozess-weite Env-Vars.
- **INV-02:** `LocalSubAgentProxy` und `CloudSubAgentProxy` implementieren dasselbe
  `SubAgentProxy`-Protocol — der DagScheduler kann beide ohne Typ-Unterscheidung nutzen.
- **INV-03:** Schlägt `LocalSubAgentProxy.execute()` fehl (inkl. Proxy-Verbindungsfehler),
  wird der Task sofort an `CloudSubAgentProxy` übergeben — kein lokaler Retry.
- **INV-04:** `api_key` erscheint nicht in Logs oder im Subprocess-Argument-String.

## Garantiertes Verhalten (Gherkin)

Siehe Artifact: `local-sub-agent-proxy-behavior.feature`
