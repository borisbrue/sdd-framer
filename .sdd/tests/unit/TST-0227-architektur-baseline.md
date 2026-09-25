---
id: TST-0227
title: "Architektur-Baseline"
level: unit
spec: SPEC-0054
contract: CON-0198
status: planned
framework: pytest
artifact: "tests/unit/test_con_0198.py"
tags: [architecture, baseline, schema]
---

# Test: Architektur-Baseline

> **Level:** unit · **Spec:** SPEC-0054 · **Contract:** CON-0198 · **Status:** planned

## Was wird geprüft?

Schema und Wirkung der Architektur-Baseline.

Schematests prüfen das Contract-Artefakt und laufen sofort. Verhaltenstests steuern die CLI über
ein temporäres Projekt mit **Shell-Sonden** (`tests/support/quality_project.py`) und sind damit
selbst sprachneutral. Sie werden mit `requires_quality_cli` übersprungen, bis der Befehl existiert.

## Vorbedingungen

- Schema-Artefakt von CON-0198.
- Für die Wirkung: `sdd arch check` ist implementiert.

## Ablauf

1. Schema mit Pflichtfeldern prüfen.
2. Baseline-Datei und Kanten vorbereiten, `sdd arch check [--json|--write-baseline]` ausführen.

## Erwartetes Ergebnis

- Passender Eintrag stuft auf `warn` herab (Exit 0), anderes Symbol passt nicht (Exit 1).
- Veralteter Eintrag zählt als `stale_baseline_entries`.
- `--write-baseline` erhält vorhandene `reason` und ergänzt neue mit „TODO“.

## Verknüpfung mit Contract

- [x] INV-01
- [x] INV-02
- [x] INV-03
- [x] INV-04
- [x] INV-05

## Verknüpfung mit Spec

FR-07
