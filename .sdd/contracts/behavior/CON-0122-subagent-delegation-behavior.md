---
id: CON-0122
project: ""
title: "Sub-Agenten-Delegations-Protokoll"
type: behavior
format: gherkin
spec: SPEC-0035
version: 0.1.0
status: draft
artifact: ".sdd/contracts/behavior/subagent-delegation-behavior.feature"
tests: ["TST-0141", "TST-0143"]
---

# Contract: Sub-Agenten-Delegations-Protokoll

> **Spec:** SPEC-0035 · **Typ:** Verhalten (Gherkin) · **Status:** draft

## Geltungsbereich

Dieser Contract gilt ausschließlich für die **Sub-Agenten-Delegation** innerhalb von
`sdd implement` (SPEC-0035). Er ist komplementär zu CON-0063 (Single-Context-Mode)
und ersetzt diesen nicht — CON-0063 gilt weiterhin für den Fallback-Pfad und für
Nicht-Claude-Provider. Retry-Mechanismen anderer Kommandos (`sdd orchestrate`,
`sdd run`) sind in CON-0095/0096/0100 geregelt und nicht Gegenstand dieses Contracts.

## Zweck

Beschreibt das beobachtbare Verhalten des Orchestrators bei der Sub-Agenten-Delegation
nach `sdd decompose`: Kontext-Übergabe pro Task, Token-Reporting, Fehler-Propagation
mit 1 Retry, und Fallback auf Single-Context-Mode bei Nicht-Claude-Provider (FR-01,
FR-02, FR-06, FR-09).

## Garantien

Die in `subagent-delegation-behavior.feature` definierten Szenarien sind
**ausführbare Spezifikation**.

- **G-01:** Jeder Sub-Agent erhält den Kontext seines eigenen Tasks: Spec-Inhalt, AGENTS.md, task-spezifische Contracts (nur die in task.con_ids referenzierten CON-IDs) und zugehörige Test-Stubs. Contracts anderer Tasks werden nicht übergeben.
- **G-02:** Bei Sub-Agenten-Fehler wird exakt 1 Retry durchgeführt (gilt nur für `sdd implement`-Sub-Agenten, nicht für orchestrate-Jobs). Nach erneutem Fehlschlag hält der Orchestrator an — kein Silent-Failure.
- **G-03:** Folge-Tasks werden nach einem nicht-behebbaren Sub-Agenten-Fehler nicht gestartet.
- **G-04:** Bei aktivem Non-Claude-Provider läuft die Implementierung im Single-Context-Mode gemäß CON-0063; der Output kennzeichnet `[Fallback: Single-Context-Mode]`.

## Invarianten

- **INV-01:** Die sequentielle Reihenfolge der Sub-Agenten entspricht der Reihenfolge im Decompose-Plan.
- **INV-02:** Token-Verbrauch wird für jeden Sub-Agenten-Aufruf separat in `token-history` persistiert (task_id + task_label gesetzt).
- **INV-03:** Beim Fallback (Single-Context-Mode) werden keine task_id-Einträge in `token-history` geschrieben.
