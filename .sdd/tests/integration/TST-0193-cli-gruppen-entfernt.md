---
id: TST-0193
project: PRJ-0001
title: "CLI-Gruppen `pattern` und `dev` entfernt"
level: integration
spec: SPEC-0044
contract: CON-0165
status: draft
framework: pytest
artifact: "tests/integration/test_tst_0193.py"
tags:
  - cli
  - cleanup
---

# Test: CLI-Gruppen `pattern` und `dev` entfernt

> **Level:** integration · **Spec:** SPEC-0044 · **Contract:** CON-0165

## Was wird geprüft?

Prüft dass `sdd pattern *` und `sdd dev *` mit Exit ≠ 0 enden,
`sdd obsidian` und `sdd pwa` weiterhin funktionieren und
`CHANGELOG.md` Migrationshinweise für beide Gruppen enthält.

## Vorbedingungen

- `sdd` CLI im PATH
- `CHANGELOG.md` existiert im Projektverzeichnis

## Ablauf

1. `sdd pattern list` aufrufen → Exit ≠ 0
2. `sdd dev start` aufrufen → Exit ≠ 0
3. `sdd obsidian --help` aufrufen → Exit 0
4. `sdd pwa --help` aufrufen → Exit 0
5. CHANGELOG.md lesen → "pattern" + "dev" im Kontext einer Entfernung

## Verknüpfung mit Contract

- [x] `sdd pattern *` schlägt fehl (Exit ≠ 0)
- [x] `sdd dev *` schlägt fehl (Exit ≠ 0)
- [x] `sdd obsidian` funktioniert
- [x] `sdd pwa` funktioniert
- [x] CHANGELOG enthält Migrationsnotizen
