---
id: CON-0042
project: PRJ-0001
title: "Schätzmethode: k=3 Nearest-Neighbor für Token-Kostenschätzung"
type: behavior
format: markdown
spec: SPEC-0011
version: 0.1.0
status: review
artifact: "contracts/behavior/estimate-nearest-neighbor.md"
tests:
- TST-0056
- TST-0057
---

# Contract: Schätzmethode – k=3 Nearest Neighbor

> **Spec:** SPEC-0011 · **Typ:** Verhalten · **Status:** review

## Zweck

Definiert das algorithmische Verhalten von `sdd estimate SPEC-XXXX`: Feature-Extraktion,
Normalisierung, Nearest-Neighbor-Berechnung und Konfidenz-Klassifikation.

## Feature-Vektor

Jede Spec wird durch folgende sieben Merkmale beschrieben (in dieser Reihenfolge):

| Index | Merkmal           | Berechnung                                         |
|-------|-------------------|----------------------------------------------------|
| 0     | `body_chars`      | Zeichenlänge des Body (ohne YAML-Frontmatter)      |
| 1     | `contract_count`  | Anzahl Einträge in `contracts:` Frontmatter        |
| 2     | `test_count`      | Anzahl Einträge in `tests:` Frontmatter            |
| 3     | `user_story_count`| Zeilen die `| US-` enthalten                       |
| 4     | `fr_count`        | Vorkommnisse von `**FR-` im Body                   |
| 5     | `dependency_count`| Anzahl Einträge in `depends_on:` Frontmatter       |
| 6     | `priority_weight` | `critical=4, high=3, medium=2, low=1`              |

## Algorithmus

1. Feature-Vektor der Ziel-Spec berechnen.
2. Alle historischen Datenpunkte (pro `spec_id` aggregiert) aus `token_usage` laden,
   für die ein Feature-Vektor berechnet werden kann (Spec-Datei muss vorhanden sein).
3. Alle Feature-Vektoren (Ziel + Kandidaten) Min-Max-normalisieren (Wertebereich 0–1).
   Wenn Min == Max für eine Dimension, wird der Range als 1.0 behandelt.
4. Euklidischen Abstand zwischen normiertem Ziel-Vektor und jedem normalisierten
   Kandidaten-Vektor berechnen.
5. Die k=3 Kandidaten mit dem kleinsten Abstand auswählen.
6. Gewichteten Durchschnitt berechnen:
   - Gewicht = 1 / (distance + 1e-9)
   - `est_input  = Σ(weight_i × input_tokens_i) / Σ(weight_i)`
   - `est_output = Σ(weight_i × output_tokens_i) / Σ(weight_i)`
7. Wenn keine Kandidaten vorhanden: Fallback-Heuristik auf Basis `body_chars`.

## Konfidenz-Klassifikation

Basiert auf der Anzahl der verfügbaren historischen `spec_id`-Gruppen in `token_usage`:

| Datenpunkte | Konfidenz |
|-------------|-----------|
| < 3         | LOW       |
| 3–9         | MEDIUM    |
| ≥ 10        | HIGH      |

Bei Konfidenz `LOW` wird eine Warnung ausgegeben.

## Budget-Alert

Wenn `cost_estimation.budget_alert_usd` konfiguriert ist und die berechneten
Kosten in USD diesen Wert überschreiten, wird eine WARNING-Box ausgegeben.
Kein Exit-Code-Fehler (nur informativ).

## Invarianten

- `sdd estimate` macht **keine** LLM-Aufrufe.
- Die Schätzung läuft in < 200 ms (nur SQLite-Lesen + lokale Berechnung).
- Die k Vergleichspunkte werden immer in der Ausgabe angezeigt (Transparenz).
