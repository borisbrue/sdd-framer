---
id: TST-0225
title: "Score-Berechnung: Normierung, Gewichtung, n/a-Semantik und Gates"
level: acceptance
spec: SPEC-0054
contract: CON-0196
status: planned
framework: pytest
artifact: "tests/acceptance/test_con_0196.py"
tags: [quality, score, gates, gherkin]
---

# Test: Score-Berechnung: Normierung, Gewichtung, n/a-Semantik und Gates

> **Level:** acceptance · **Spec:** SPEC-0054 · **Contract:** CON-0196 · **Status:** planned

## Was wird geprüft?

Alle 17 Szenarien der Score-Berechnung: Normierung, Gewichtung, n/a-Regeln, Architektur- und Anforderungsscore, Gates.

Schematests prüfen das Contract-Artefakt und laufen sofort. Verhaltenstests steuern die CLI über
ein temporäres Projekt mit **Shell-Sonden** (`tests/support/quality_project.py`) und sind damit
selbst sprachneutral. Sie werden mit `requires_quality_cli` übersprungen, bis der Befehl existiert.

## Vorbedingungen

- `sdd quality measure` und `sdd config validate` (Gate-Prüfung) sind implementiert, sonst übersprungen.

## Ablauf

1. Standardprojekt mit Test-, Metrik- und Abhängigkeitssonde (Shell) anlegen.
2. Je Szenario Sondenausgaben, `quality.yaml` und `config.yaml` (`quality:`) setzen.
3. `sdd quality measure --json` ausführen und Zahlen im Report prüfen.

## Erwartetes Ergebnis

- Die Zahlen aus den Beispieltabellen des Contracts (z. B. 0,825; 0,8333; 0,5; 0,7; 0,6; 0,8; 0,4).
- Gates fail-closed mit Exit 1; ungültige Gates sind Konfigurationsfehler (Exit 1 bei `config validate`, Exit 2 bei `measure`).

## Verknüpfung mit Contract

- [x] INV-01
- [x] INV-02
- [x] INV-03
- [x] INV-04
- [x] INV-06

## Verknüpfung mit Spec

FR-03, FR-04, FR-05, FR-08, FR-09, FR-10, FR-11
