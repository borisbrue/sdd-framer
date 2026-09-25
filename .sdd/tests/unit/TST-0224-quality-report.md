---
id: TST-0224
title: "Quality-Report"
level: unit
spec: SPEC-0054
contract: CON-0195
status: planned
framework: pytest
artifact: "tests/unit/test_con_0195.py"
tags: [quality, report, schema]
---

# Test: Quality-Report

> **Level:** unit · **Spec:** SPEC-0054 · **Contract:** CON-0195 · **Status:** planned

## Was wird geprüft?

Schema des Quality-Reports und seine Querbeziehungen an einem echten Report.

Schematests prüfen das Contract-Artefakt und laufen sofort. Verhaltenstests steuern die CLI über
ein temporäres Projekt mit **Shell-Sonden** (`tests/support/quality_project.py`) und sind damit
selbst sprachneutral. Sie werden mit `requires_quality_cli` übersprungen, bis der Befehl existiert.

## Vorbedingungen

- Schema-Artefakt von CON-0195.
- Für die Querbeziehungen: `sdd quality measure --json` ist implementiert.

## Ablauf

1. Beispielreport aus dem Contract gegen das Schema prüfen, gezielt Pflichtfelder entfernen.
2. Report aus einem Standardprojekt erzeugen und Invarianten prüfen.

## Erwartetes Ergebnis

- `score` ∈ [0,1] oder `null`; jedes `null`/`n/a` mit `reason`; Verstöße mit `adr` und `symbol`.
- `score` = Wurzel; `incomplete` genau bei `null` im Baum; jede FR genau einmal; `unbekannt` nur bei ausgefallener Testsonde; Sonden vollständig in Deklarationsreihenfolge.

## Verknüpfung mit Contract

- [x] INV-01
- [x] INV-02
- [x] INV-03
- [x] INV-04
- [x] INV-05
- [x] INV-06
- [x] INV-07
- [x] INV-08

## Verknüpfung mit Spec

FR-09, FR-12
