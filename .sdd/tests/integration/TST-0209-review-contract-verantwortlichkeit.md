---
id: TST-0209
project: PRJ-0001
title: "Verantwortlichkeitstrennung `sdd review contract` vs. `sdd test generate`"
level: integration
spec: SPEC-0044
contract: CON-0170
status: draft
framework: pytest
artifact: "tests/integration/test_tst_0198.py"
tags:
  - cli
  - cleanup
---

# Test: Verantwortlichkeitstrennung review vs. test generate

> **Level:** integration · **Spec:** SPEC-0044 · **Contract:** CON-0170

## Was wird geprüft?

Prüft dass `sdd review contract` keine TST-Dateien anlegt, und `sdd test generate`
der einzige Befehl ist, der TST-Dateien erstellt.

## Vorbedingungen

- `sdd` CLI im PATH nach Implementierung von SPEC-0044
- Test läuft in einem temporären Projektverzeichnis (Isolation)

## Ablauf

1. Zähle TST-Dateien vor `sdd review contract CON-0165`
2. `sdd review contract CON-0165` aufrufen
3. Zähle TST-Dateien nach dem Aufruf → Anzahl unverändert
4. `sdd test generate --help` → Exit 0 (Befehl existiert)

## Verknüpfung mit Contract

- [x] `sdd review contract` legt keine TST-Dateien an
- [x] `sdd test generate` existiert als eigenständiger Befehl
