---
id: TST-0194
project: PRJ-0001
title: "Kanonische Verb-Gruppen `sdd new` und `sdd review`"
level: integration
spec: SPEC-0044
contract: CON-0166
status: draft
framework: pytest
artifact: "tests/integration/test_tst_0194.py"
tags:
  - cli
  - cleanup
---

# Test: Kanonische Verb-Gruppen `sdd new` und `sdd review`

> **Level:** integration · **Spec:** SPEC-0044 · **Contract:** CON-0166

## Was wird geprüft?

Prüft dass alle neuen kanonischen Befehle aufrufbar sind, alte Formen
mit Exit ≠ 0 und Migrationshinweis enden, und `sdd contract analyze`
die Namenskollision auflöst.

## Vorbedingungen

- `sdd` CLI im PATH nach Implementierung von SPEC-0044

## Ablauf

1. `sdd new hotfix --help` → Exit 0
2. `sdd review spec --help` → Exit 0
3. `sdd review contract --help` → Exit 0
4. `sdd review pending --help` → Exit 0
5. `sdd holdout generate --help` → Exit 0
6. `sdd test run --help` → Exit 0
7. `sdd contract analyze --help` → Exit 0
8. `sdd generate-holdouts` → Exit ≠ 0 + Hinweis auf `sdd holdout generate`
9. `sdd evaluate` → Exit ≠ 0 + Hinweis auf `sdd holdout run`

## Verknüpfung mit Contract

- [x] `sdd new hotfix` verfügbar
- [x] `sdd review` Gruppe vorhanden (spec, contract, pending)
- [x] `sdd holdout generate/run` verfügbar
- [x] `sdd test run/results` verfügbar
- [x] `sdd contract analyze` löst Namenskollision auf
- [x] Alte Befehlsformen geben Migrationshinweis
