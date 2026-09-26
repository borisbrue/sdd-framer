---
id: CON-0095
title: "Task-Lifecycle – Zustandsübergänge der Distribution Engine"
type: behavior
format: gherkin
spec: SPEC-0026
version: 0.1.0
status: deprecated
artifact: "contracts/behavior/task-lifecycle.feature"
tests:
- TST-0114
deprecated_reason: "mit SPEC-0026 abgelöst: Distribution Engine ohne Codeerzeugung; abgelöst durch die Rollen-Pipeline"
---

# Contract: Task-Lifecycle – Zustandsübergänge der Distribution Engine

> **Spec:** SPEC-0026 · **Typ:** Verhalten (Gherkin) · **Status:** draft

## Zweck

Legt fest, welche Zustandsübergänge ein Task durchläuft – von der Ableitung aus
dem Spec bis zum Commit auf dem Spec-Branch oder zur Blockierung nach maximalen
Retries.

## Garantien

Ein Task startet in `pending`, wird einem LLM zugewiesen (`assigned`), läuft im
Container (`running`), wird geprüft (`review`) und endet entweder als
`committed` (positiv) oder `blocked` (nach 3 fehlgeschlagenen Versuchen).

## Invarianten

- **INV-01:** Ein Task kann nie direkt von `pending` nach `committed` springen.
- **INV-02:** Die Retry-Zahl überschreitet nie 3.
- **INV-03:** Jeder `committed`-Task hat einen zugehörigen Git-Commit-Hash.

## Begriffe

| Begriff | Definition |
|---|---|
| Task | Atomare Implementierungsaufgabe, abgeleitet aus einem Spec |
| ReviewPipeline | Kette aus Syntax-Check, Unit-Tests und Claude-Code-Review |
| Retry | Wiederholung eines Tasks mit erweitertem Fehlerkontext |
