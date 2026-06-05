---
id: TST-0149
project: ""
title: "DagScheduler: Task-Reihenfolge, parallele Slots und Observer-Dispatch"
level: unit
spec: SPEC-0036
contract: CON-0127
status: planned
framework: pytest
artifact: "tests/unit/test_tst_0149.py"
tags: []
---

# Test: DagScheduler – Abhängigkeiten und Parallelität

> **Level:** unit · **Spec:** SPEC-0036 · **Contract:** CON-0127 · **Status:** planned

## Was wird geprüft?

Ob `DagScheduler.run()` Task-Abhängigkeiten korrekt durchsetzt, parallele Slots
getrennt für lokal/cloud zählt, Observer-Events nach Completion dispatcht und
zyklische Abhängigkeiten erkennt (FR-01, FR-05).

## Vorbedingungen

- `SubAgentProxy.execute()` via Mock ersetzbar (sofortige Completion simulierbar)
- Async-Execution via `ThreadPoolExecutor`-Mock oder synchroner Test-Modus
- Dispatch-Reihenfolge via Aufruf-Log messbar

## Ablauf

1. DAG mit Task-A und Task-B (root, beide lokal, max_parallel_local=2) →
   beide werden gleichzeitig dispatcht
2. DAG mit Task-A → Task-B (abhängig) → Task-A zuerst, Task-B erst nach A completed
3. DAG mit Task-A, B, C (alle lokal, max_parallel_local=2) → maximal 2 gleichzeitig,
   dritter startet erst nach Completion eines der ersten zwei
4. DAG mit Task-A (lokal) und Task-B (cloud), max_parallel_local=2, max_parallel_cloud=1 →
   lokale und Cloud-Slots unabhängig, kein gegenseitiges Blockieren
5. DAG mit Task-A.depends_on=[Task-B] und Task-B.depends_on=[Task-A] →
   `ValueError` wird geraist, kein Task dispatcht
6. Nach Completion von Task-A → Observer prüft Task-B (hängt von A ab) und dispatcht es

## Erwartetes Ergebnis

- Fall 1: Beide Proxy-Mocks gleichzeitig aufgerufen
- Fall 2: Proxy-Mock für B erst nach Completion von A aufgerufen
- Fall 3: Nie mehr als 2 gleichzeitige lokale Proxy-Aufrufe
- Fall 4: Cloud-Slot und lokaler Slot unabhängig
- Fall 5: `ValueError` mit Zyklus-Hinweis, `execute` nicht aufgerufen
- Fall 6: Task-B-Dispatch nach Task-A-Completion nachweisbar

## Verknüpfung mit Contract

- [x] INV-01: depends_on wird strikt durchgesetzt
- [x] INV-02: max_parallel_local / max_parallel_cloud nie überschritten
- [x] INV-03: Root-Tasks sofort dispatcht
- [x] INV-04: Observer-getriebener Dispatch (kein Polling)
