---
id: TST-0220
title: sdd config validate – CLI Exit-Codes und JSON-Output
level: contract
spec: SPEC-0052
contract: CON-0191
status: planned
framework: pytest
artifact: tests/contract/test_con0191_config_validate_cli.py
tags:
- config
- cli
- contract
- json
---

# Test: sdd config validate – CLI Exit-Codes und JSON-Output

> **Level:** contract · **Spec:** SPEC-0052 · **Contract:** CON-0191 · **Status:** planned

## Was wird geprüft?

Das CLI-Verhalten von `sdd config validate` end-to-end via `subprocess`:
- Exit-Code 0 bei valider Config
- Exit-Code 0 bei Config mit nur Warnings (anthropic ohne key)
- Exit-Code 1 bei fehlenden Pflichtfeldern
- `--json` liefert valides JSON-Array mit `{level, path, message}`
- `--json` bei valider Config → `[]`
- `--json` bei Warning → Array mit warning-Eintrag, Exit-Code 0
- `--json` unterdrückt Rich-Markup (kein ANSI in stdout)
- Fehlende config.yaml → Exit-Code 1 + klare Meldung
- Ungültiges YAML → Exit-Code 1 + YAML-Fehlerhinweis
- `sdd validate` (bestehender Befehl) bleibt unverändert

## Vorbedingungen

- `sdd` CLI installiert und im PATH
- `tmp_path` pytest-Fixture für isolierte config.yaml-Dateien

## Ablauf

1. Temporäres Projektverzeichnis mit/ohne config.yaml anlegen
2. `subprocess.run(["sdd", "config", "validate", ...], cwd=tmp_path)` aufrufen
3. Exit-Code und stdout prüfen

## Erwartetes Ergebnis

Gemäß CON-0191-Szenarien (alle 10 Szenarien abgedeckt).

## Negativfälle / Edge Cases

- Fehlende config.yaml (kein Projektverzeichnis)
- Syntaktisch ungültiges YAML (`key: [ungültig`)
- ANSI-freie JSON-Ausgabe bei `--json`

## Verknüpfung mit Contract

- [x] FR-06: CLI-Integration (Exit-Codes)
- [x] FR-07: JSON-Output (`--json`)
- [x] INV-01: Exit-Code immer 0 oder 1
- [x] INV-02: `--json` immer valides Array
- [x] INV-03: `sdd validate` bleibt unverändert
