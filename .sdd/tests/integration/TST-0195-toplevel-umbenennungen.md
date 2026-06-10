---
id: TST-0195
project: PRJ-0001
title: "Top-Level-Befehle in Gruppen `sdd spec` und `sdd autonomy`"
level: integration
spec: SPEC-0044
contract: CON-0167
status: draft
framework: pytest
artifact: "tests/integration/test_tst_0195.py"
tags:
  - cli
  - cleanup
---

# Test: Top-Level-Umbenennungen

> **Level:** integration · **Spec:** SPEC-0044 · **Contract:** CON-0167

## Was wird geprüft?

Prüft dass `sdd spec solid`, `sdd spec regression` und `sdd autonomy *`
aufrufbar sind, und `sdd status-check` als öffentlicher Befehl nicht mehr verfügbar ist.

## Vorbedingungen

- `sdd` CLI im PATH nach Implementierung von SPEC-0044

## Ablauf

1. `sdd spec solid --help` → Exit 0
2. `sdd spec regression --help` → Exit 0
3. `sdd autonomy level --help` → Exit 0
4. `sdd autonomy set-level --help` → Exit 0
5. `sdd autonomy false-positive --help` → Exit 0
6. `sdd status-check` → Exit ≠ 0

## Verknüpfung mit Contract

- [x] `sdd spec solid` ersetzt `sdd solid-check`
- [x] `sdd spec regression` ersetzt `sdd regression-check`
- [x] `sdd autonomy level/set-level/false-positive` verfügbar
- [x] `sdd status-check` nicht mehr öffentlich
