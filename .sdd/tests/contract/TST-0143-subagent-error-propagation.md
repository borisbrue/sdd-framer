---
id: TST-0143
project: ""
title: "Fehler-Propagation: Sub-Agenten-Fehler hält Orchestrator an"
level: contract
spec: SPEC-0035
contract: CON-0122
status: planned
framework: "pytest"
artifact: "tests/contract/test_tst_0143.py"
tags: []
---

# Test: Fehler-Propagation Sub-Agenten

> **Level:** contract · **Spec:** SPEC-0035 · **Contract:** CON-0122 · **Status:** planned

## Was wird geprüft?

Ob der Orchestrator bei Sub-Agenten-Fehler exakt 1 Retry durchführt, danach anhält
und Folge-Tasks nicht startet (G-02, G-03 von CON-0122, FR-06).

## Vorbedingungen

- Orchestrator-Logik isolierbar (Sub-Agent mockbar)
- Testdaten: Spec mit 3 Tasks, Task 2 wirft Fehler

## Ablauf

1. Sub-Agenten-Mock für Task 2 konfigurieren: erste Ausführung → Exception
2. Sub-Agenten-Mock für Task 2 (Retry): zweite Ausführung → Exception
3. Orchestrator mit 3-Task-Plan ausführen
4. Prüfen: Task 1 wurde ausgeführt
5. Prüfen: Task 2 wurde genau 2× versucht (1 Initial + 1 Retry)
6. Prüfen: Task 3 wurde nicht gestartet
7. Prüfen: Fehlerbericht enthält Task-ID und Fehlermeldung

## Erwartetes Ergebnis

- Task 1: success
- Task 2: 2 Versuche, dann OrchestratorError o.Ä.
- Task 3: nie gestartet
- Exception/Fehlerbericht: nicht-leer, enthält "Task 2" oder task_id

## Verknüpfung mit Contract

- [x] G-02: Exakt 1 Retry, dann Halt
- [x] G-03: Folge-Tasks nicht gestartet nach Fehler
- [x] INV-01: Sequentielle Reihenfolge eingehalten
