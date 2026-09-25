---
id: TST-0226
title: "CLI sdd quality, sdd arch und Test-Run-Erweiterung"
level: acceptance
spec: SPEC-0054
contract: CON-0197
status: planned
framework: pytest
artifact: "tests/acceptance/test_con_0197.py"
tags: [quality, cli, arch, validate, gherkin]
---

# Test: CLI sdd quality, sdd arch und Test-Run-Erweiterung

> **Level:** acceptance · **Spec:** SPEC-0054 · **Contract:** CON-0197 · **Status:** planned

## Was wird geprüft?

Alle 25 CLI-Szenarien: `sdd quality measure|doctor|init`, `sdd arch check|init`, `sdd test run` mit Testsonde, ADR-Prüfung in `sdd validate`.

Schematests prüfen das Contract-Artefakt und laufen sofort. Verhaltenstests steuern die CLI über
ein temporäres Projekt mit **Shell-Sonden** (`tests/support/quality_project.py`) und sind damit
selbst sprachneutral. Sie werden mit `requires_quality_cli` übersprungen, bis der Befehl existiert.

## Vorbedingungen

- `sdd quality` und `sdd arch` sind implementiert, sonst übersprungen.
- `git` im PATH (Diff- und Wiederverwendungstests).

## Ablauf

1. Temporäres Projekt je Szenario, bei Bedarf als Git-Repo.
2. Befehle über click `CliRunner` ausführen; stdout (JSON) und stderr getrennt prüfen.

## Erwartetes Ergebnis

- Exit-Codes je Befehl laut Contract-Tabelle.
- Kein Überschreiben ohne `.new`, außer `--out` und `--write-baseline`.
- Run-Report mit `junit`, `testcases`, `git_sha`; ohne `quality.yaml` unverändert.
- Keine Sprach- oder Werkzeugnamen in Befehlsnamen.

## Verknüpfung mit Contract

- [x] INV-01
- [x] INV-02
- [x] INV-03
- [x] INV-04
- [x] INV-05
- [x] INV-05a
- [x] INV-06
- [x] INV-07
- [x] INV-08

## Verknüpfung mit Spec

FR-01, FR-03, FR-06, FR-07, FR-13, FR-14
