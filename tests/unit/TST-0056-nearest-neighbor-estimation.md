---
id: TST-0056
project: PRJ-0001
title: "k=3 Nearest-Neighbor: Feature-Extraktion und Schätzgenauigkeit"
level: unit
spec: SPEC-0011
contract: CON-0042
status: planned
framework: pytest
artifact: "tests/unit/test_estimation.py"
tags: ["nearest-neighbor", "estimation", "features"]
---

# Test: k=3 Nearest-Neighbor – Feature-Extraktion und Schätzgenauigkeit

> **Level:** unit · **Spec:** SPEC-0011 · **Contract:** CON-0042 · **Status:** planned

## Was wird geprüft?

- `extract_features()` gibt korrekten Feature-Vektor zurück
- k=3 NN wählt die 3 nächsten Nachbarn aus einem bekannten Datensatz
- Gewichteter Durchschnitt ist korrekt
- Fallback bei leerer DB

## Ablauf

### TC-01: Feature-Extraktion

Gegeben eine Spec-Datei mit:
- Body: 500 Zeichen
- `contracts: ["CON-0001"]` → 1
- `tests: ["TST-0001", "TST-0002"]` → 2
- Body enthält 3 Zeilen mit `| US-` → 3
- Body enthält 5 Vorkommnisse von `**FR-` → 5
- `depends_on: ["SPEC-0001"]` → 1
- `priority: high` → 3

Prüfe: `extract_features()` liefert `SpecFeatures(body_chars=500, contract_count=1,
test_count=2, user_story_count=3, fr_count=5, dependency_count=1, priority_weight=3)`.

### TC-02: k=3 NN aus bekanntem Datensatz

Gegeben 5 historische Punkte mit bekannten Feature-Vektoren.
Kontrollrechnung des euklidischen Abstands per Hand.
Prüfe: Die 3 zurückgegebenen Nachbarn sind genau die 3 mit dem kleinsten Abstand.

### TC-03: Gewichteter Durchschnitt

Gegeben 2 Nachbarn mit Abstand 0.1 (1000 Input, 400 Output) und 0.9 (200 Input, 80 Output).
Prüfe: Schätzung liegt näher an den Werten des ersten Nachbarn (kleinerer Abstand).

### TC-04: Fallback bei leerer DB

Gegeben leere `evaluations.db` (keine token_usage-Einträge).
Prüfe: `estimate()` gibt `EstimateResult` mit `confidence="LOW"` zurück,
kein Exception, `n_data_points=0`.

## Erwartetes Ergebnis

Alle 4 Test-Cases bestehen ohne LLM-Aufrufe.
