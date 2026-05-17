---
id: TST-0037
title: "Execution Gate – Phase State Machine"
level: contract
spec: SPEC-0014
contract: CON-0025
status: implemented
framework: pytest
artifact: "tests/contract/test_con-0025.py"
tags: [gate, phase, state-machine]
---

# Test: Execution Gate – Phase State Machine (CON-0025)

> **Level:** contract · **Spec:** SPEC-0014 · **Contract:** CON-0025

## Was wird geprüft?

Das korrekte Verhalten der Phasenzustandsmaschine: execute ist nur erlaubt wenn `pipeline_phase == execute-unlocked`, force-Execute erfordert `--override-reason`, und jede Phase setzt ihre Vorgängerin voraus.

## Vorbedingungen

- `tool/sdd_cli/gate.py` implementiert (`ExecutionGate`)
- Temporäres Verzeichnis als `repo_root`

## Ablauf

1. `ExecutionGate.check()` mit nicht freigegebenem Gate → `blocked=True, exit_code=2`
2. `ExecutionGate.check()` mit `pipeline_phase=execute-unlocked` → `blocked=False`
3. `force_execute()` ohne Begründung → `exit_code=1`
4. `force_execute()` mit Begründung → Override in JSON geloggt
5. `can_start_phase()` wenn Vorgänger fehlt → `allowed=False`
6. Phase kann nach `mark_phase_started()` neu gestartet werden
7. Phasenstatus wird crashsicher persistiert

## Erwartetes Ergebnis

Alle 8 Szenarien aus `execution-gate-phase-state-machine.feature` passen zu den Invarianten INV-01 bis INV-08 in CON-0025.

## Verknüpfung mit Contract

- [x] INV-01: Execute nur bei `execute-unlocked`
- [x] INV-02: Force ohne Reason → exit 1
- [x] INV-03: Force mit Reason → Override geloggt
- [x] INV-04: Phase blockiert wenn Vorgänger nicht ok
- [x] INV-05: Re-Run möglich nach `mark_phase_started`
- [x] INV-07: Persistenz crash-safe (sofort nach Abschluss)
