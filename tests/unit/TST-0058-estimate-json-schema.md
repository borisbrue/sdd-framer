---
id: TST-0058
project: PRJ-0001
title: "estimate --json: Schema-Validierung des JSON-Outputs"
level: unit
spec: SPEC-0011
contract: CON-0043
status: planned
framework: pytest
artifact: "tests/unit/test_estimation.py"
tags: ["json-schema", "estimation", "output"]
---

# Test: `estimate --json` – Schema-Validierung

> **Level:** unit · **Spec:** SPEC-0011 · **Contract:** CON-0043 · **Status:** planned

## Was wird geprüft?

- `EstimateResult.to_dict()` enthält alle Pflichtfelder gemäß CON-0043
- `confidence` ist exakt `LOW`, `MEDIUM` oder `HIGH`
- `neighbors` enthält maximal 3 Einträge
- `similarity` liegt in [0.0, 1.0]

## Ablauf

### TC-01: Pflichtfelder vorhanden

1. Erstelle `EstimateResult` mit Testdaten
2. Rufe `.to_dict()` auf
3. Prüfe: Alle Required-Felder aus CON-0043 vorhanden

### TC-02: Gültige confidence-Werte

Prüfe dass `confidence` ∈ {"LOW", "MEDIUM", "HIGH"}.

### TC-03: neighbors.similarity ∈ [0, 1]

Gegeben 3 Nachbarn.
Prüfe: `similarity` für jeden Nachbarn im Bereich [0.0, 1.0].

### TC-04: --all Output enthält estimates-Liste

Prüfe: `{"estimates": [<EstimateResult>, ...]}` für `--all`-Modus (dict check).

## Erwartetes Ergebnis

Alle 4 Test-Cases bestehen ohne Dateisystem-Zugriff.
