---
id: CON-0127
project: ""
title: "DagScheduler – Abhängigkeits- und Parallelitäts-Contract"
type: behavior
format: gherkin
spec: SPEC-0036
version: 0.1.0
status: draft
artifact: ".sdd/contracts/behavior/dag-scheduler-behavior.feature"
tests: ["TST-0149"]
---

# Contract: DagScheduler – Abhängigkeits- und Parallelitäts-Contract

> **Spec:** SPEC-0036 · **Typ:** Verhalten (Gherkin) · **Status:** draft

## Geltungsbereich

Dieser Contract gilt für `DagScheduler.run()` in SPEC-0036 (FR-01, FR-05).
Er beschreibt das beobachtbare Dispatch-Verhalten: Task-Reihenfolge, parallele
Slots und Observer-Benachrichtigung bei Task-Abschluss.

## Invarianten

- **INV-01:** Ein Task wird erst dispatcht wenn alle Tasks in `depends_on` den
  Status `completed` haben — keine Ausnahme.
- **INV-02:** Die Anzahl gleichzeitig laufender lokaler Tasks überschreitet nie
  `max_parallel_local`; die Anzahl gleichzeitig laufender Cloud-Tasks überschreitet
  nie `max_parallel_cloud`.
- **INV-03:** Tasks ohne `depends_on` (root-Tasks) werden sofort dispatcht sobald
  ein freier Slot verfügbar ist.
- **INV-04:** Der Scheduler dispatcht den nächsten bereiten Task ereignisgesteuert
  nach Task-Completion — kein Polling-Loop.

## Garantiertes Verhalten (Gherkin)

Siehe Artifact: `dag-scheduler-behavior.feature`
