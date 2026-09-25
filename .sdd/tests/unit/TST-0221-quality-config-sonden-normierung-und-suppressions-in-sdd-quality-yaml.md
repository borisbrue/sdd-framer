---
id: TST-0221
title: "Quality-Config: Sonden, Normierung und Suppressions in .sdd/quality.yaml"
level: unit
spec: SPEC-0054
contract: CON-0192
status: planned
framework: pytest
artifact: "tests/unit/test_con_0192.py"
tags: [quality, config, schema]
---

# Test: Quality-Config: Sonden, Normierung und Suppressions in .sdd/quality.yaml

> **Level:** unit · **Spec:** SPEC-0054 · **Contract:** CON-0192 · **Status:** planned

## Was wird geprüft?

Das Schema von `.sdd/quality.yaml` und die Laufzeitregeln der Sonden.

Schematests prüfen das Contract-Artefakt und laufen sofort. Verhaltenstests steuern die CLI über
ein temporäres Projekt mit **Shell-Sonden** (`tests/support/quality_project.py`) und sind damit
selbst sprachneutral. Sie werden mit `requires_quality_cli` übersprungen, bis der Befehl existiert.

## Vorbedingungen

- Schema-Artefakt von CON-0192 liegt unter `.sdd/contracts/data/`.
- Für die Laufzeittests: `sdd quality` ist implementiert (sonst werden sie übersprungen).

## Ablauf

1. Gültige und ungültige Instanzen gegen das JSON-Schema prüfen (INV-01 bis INV-04).
2. Temporäres Projekt mit Shell-Sonden anlegen (`tests/support/quality_project.py`).
3. `sdd quality measure`/`doctor` ausführen und Sondenstatus bzw. Exit-Code prüfen.

## Erwartetes Ergebnis

- Schema lehnt fehlendes `{out}`, `role: tests` ohne junit/fr_marker, `fr_marker` ohne Testrolle und unbekannte Formate ab.
- Zwei Sonden mit derselben Rolle → Exit 2 mit beiden Namen.
- Metrik ohne Normierung → `doctor` Exit 1, „Normierung fehlt“.
- Jeder der fünf Ausfallgründe (INV-09) erscheint wörtlich als `reason`; Exit ≠ 0 mit gültiger Ausgabe bleibt `ok`.

## Verknüpfung mit Contract

- [x] INV-01
- [x] INV-02
- [x] INV-03
- [x] INV-04
- [x] INV-05
- [x] INV-09

## Verknüpfung mit Spec

FR-01, FR-02, FR-11, FR-13
