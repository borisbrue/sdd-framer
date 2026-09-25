---
id: TST-0223
title: "Architekturregeln und Baseline"
level: unit
spec: SPEC-0054
contract: CON-0194
status: planned
framework: pytest
artifact: "tests/unit/test_con_0194.py"
tags: [architecture, rules, strategy]
---

# Test: Architekturregeln und Baseline

> **Level:** unit · **Spec:** SPEC-0054 · **Contract:** CON-0194 · **Status:** planned

## Was wird geprüft?

Schema und Auswertung der Architekturregeln, eine Testgruppe je Regelart (Strategy).

Schematests prüfen das Contract-Artefakt und laufen sofort. Verhaltenstests steuern die CLI über
ein temporäres Projekt mit **Shell-Sonden** (`tests/support/quality_project.py`) und sind damit
selbst sprachneutral. Sie werden mit `requires_quality_cli` übersprungen, bis der Befehl existiert.

## Vorbedingungen

- Schema-Artefakt von CON-0194.
- Für die Auswertung: `sdd arch check --json` ist implementiert.

## Ablauf

1. Schema mit allen vier Regelarten und Negativfällen prüfen.
2. Je Regelart vorbereitete `sdd-deps`-Kanten über eine Shell-Sonde liefern und `sdd arch check --json` auswerten.

## Erwartetes Ergebnis

- Genau die erwarteten Verstöße als Schlüssel `(rule, file, symbol)`; Zeile und ADR im Verstoß.
- Erste passende Schicht gewinnt; Dateien ohne Schicht werden ignoriert.
- Fehlende Kantenart und unbekannte Schicht → Regel in `rules_na` mit Grund; unaufgelöste Kanten zählen, sind aber kein Verstoß.
- Verstoß-Schlüssel ist stabil gegen Zeilenverschiebung.

## Verknüpfung mit Contract

- [x] INV-01
- [x] INV-02
- [x] INV-03
- [x] INV-04
- [x] INV-05
- [x] INV-06
- [x] INV-07
- [x] INV-08
- [x] INV-09

## Verknüpfung mit Spec

FR-05, FR-07
