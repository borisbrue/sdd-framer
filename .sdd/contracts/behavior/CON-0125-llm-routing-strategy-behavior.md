---
id: CON-0125
project: ""
title: "LlmRoutingStrategy – Routing-Entscheidungs-Contract"
type: behavior
format: gherkin
spec: SPEC-0036
version: 0.1.0
status: deprecated
artifact: ".sdd/contracts/behavior/llm-routing-strategy-behavior.feature"
tests: ["TST-0147"]
deprecated_reason: "mit SPEC-0036 abgelöst: Lokaler Agent und DagScheduler nie angebunden; abgelöst durch die Rollen-Pipeline"
---

# Contract: LlmRoutingStrategy – Routing-Entscheidungs-Contract

> **Spec:** SPEC-0036 · **Typ:** Verhalten (Gherkin) · **Status:** draft

## Geltungsbereich

Dieser Contract gilt für `ContextSizeRoutingStrategy.route()` in SPEC-0036 (FR-02, FR-03).
Er beschreibt das beobachtbare Routing-Verhalten ausschließlich auf Basis von Token-Zählung
und Konfiguration — nicht das interne Zählverfahren.

## Invarianten

- **INV-01:** `route()` gibt ausschließlich `"local"` oder `"cloud"` zurück — kein anderer Wert.
- **INV-02:** Ist `local_agent.enabled = false`, gibt `route()` immer `"cloud"` zurück,
  unabhängig von der Token-Größe.
- **INV-03:** Die Entscheidung ist deterministisch: identischer TaskContext + identische
  Konfiguration → immer dasselbe Ergebnis.
- **INV-04:** `route()` verursacht keinen Netzwerkaufruf — die Token-Zählung erfolgt
  vollständig lokal via tiktoken.

## Garantiertes Verhalten (Gherkin)

Siehe Artifact: `llm-routing-strategy-behavior.feature`
