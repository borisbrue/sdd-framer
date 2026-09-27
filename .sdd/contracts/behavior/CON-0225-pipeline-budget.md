---
id: CON-0225
title: "Pipeline-Budget"
type: behavior
format: gherkin
spec: SPEC-0063
version: 0.1.0
status: approved
artifact: ".sdd/contracts/behavior/pipeline-budget.feature"
tests: ["TST-0254"]
---

# Contract: Pipeline-Budget

> **Spec:** SPEC-0063 · **Typ:** Verhalten (Gherkin) · **Status:** approved

## Zweck

Legt das Token-Budget eines Pipeline-Runs fest (SPEC-0063 FR-01). Es ist ein allgemeines Feature der Pipeline, der Benchmark setzt es nur.

## Garantien

Die Szenarien im Artifact (`.sdd/contracts/behavior/pipeline-budget.feature`) sind **ausführbare Spezifikation**; Rollen laufen gegen den Fake-LLM-Server.

## Invarianten

- **INV-01:** `pipeline.budget.max_tokens` und `pipeline.budget.max_claude_tokens` (ganze Zahlen > 0) begrenzen jeden Run; die Run-Optionen `--max-tokens` und `--max-claude-tokens` überschreiben sie für einen Run und stehen unter `options.budget` in `run.json`. Ohne Angabe gibt es kein Budget.
- **INV-02:** Nach jedem Rollenaufruf zählt die Pipeline die Usage des Runs aus `token_usage` (`run_id` des Runs nach CON-0206, Eingabe- plus Ausgabe-Tokens). Claude-Tokens sind die Zeilen der Rollen, die laut `run.json` mit `claude-cli` oder `anthropic` belegt sind. Rollen im Modus `session` zählen nicht: Claude Code im Dialog ist kein Provider-Aufruf und wird nicht erfasst (CON-0207, vgl. CON-0013).
- **INV-03:** Ist ein Budget überschritten, hält der Run: `state.status` `halted`, Ereignis `transition` nach `halted` mit Grund `budget` und dem Zählstand, Exit 1. Ein angefangener Rollenaufruf wird zu Ende geführt, danach startet keiner mehr.
- **INV-04:** Ein Budget ≤ 0 oder keine ganze Zahl ist ein Konfigurationsfehler: `sdd config validate` meldet ihn als Fehler (Regel ergänzt CON-0190 additiv, Exit-Code nach CON-0191), `sdd pipeline run` bricht beim Start mit Exit 2 ab.
