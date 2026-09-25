---
id: TST-0222
title: "Austauschformate sdd-deps, sdd-metrics und sdd-findings"
level: unit
spec: SPEC-0054
contract: CON-0193
status: planned
framework: pytest
artifact: "tests/unit/test_con_0193.py"
tags: [quality, exchange-format, schema]
---

# Test: Austauschformate sdd-deps, sdd-metrics und sdd-findings

> **Level:** unit · **Spec:** SPEC-0054 · **Contract:** CON-0193 · **Status:** planned

## Was wird geprüft?

Die Austauschformate `sdd-deps`, `sdd-metrics`, `sdd-findings` und ihre Gleichwertigkeit mit SARIF.

Schematests prüfen das Contract-Artefakt und laufen sofort. Verhaltenstests steuern die CLI über
ein temporäres Projekt mit **Shell-Sonden** (`tests/support/quality_project.py`) und sind damit
selbst sprachneutral. Sie werden mit `requires_quality_cli` übersprungen, bis der Befehl existiert.

## Vorbedingungen

- Schema-Artefakt von CON-0193.
- Für die Verbrauchertests: `sdd quality measure` ist implementiert.

## Ablauf

1. Gültige/ungültige Instanzen je Format gegen das Schema prüfen.
2. Dieselben Befunde einmal als SARIF, einmal als `sdd-findings` liefern und `lint_per_kloc` vergleichen.

## Erwartetes Ergebnis

- Relative Pfade, `unresolved` bei `to: null`, `symbol` Pflicht, `args` nur bei `call`, snake_case-Metriknamen, geschlossene Severity.
- SARIF und `sdd-findings` ergeben dieselbe normierte Metrik (INV-08).
- Unvollständige Datei → Sonde `n/a`, „Ausgabe nicht parsebar“ (INV-01).

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

FR-02, FR-08
