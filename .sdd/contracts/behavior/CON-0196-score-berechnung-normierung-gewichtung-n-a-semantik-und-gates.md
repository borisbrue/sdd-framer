---
id: CON-0196
title: "Score-Berechnung: Normierung, Gewichtung, n/a-Semantik und Gates"
type: behavior
format: gherkin
spec: SPEC-0054
version: 0.1.0
status: draft
artifact: ".sdd/contracts/behavior/score-berechnung-normierung-gewichtung-n-a-semantik-und-gates.feature"
tests: ["TST-0225"]
---

# Contract: Score-Berechnung: Normierung, Gewichtung, n/a-Semantik und Gates

> **Spec:** SPEC-0054 · **Typ:** Verhalten (Gherkin) · **Status:** draft

## Zweck

Legt fest, wie aus Sondenergebnissen Metriken, Teilscores, der Gesamtscore und Gate-Entscheidungen
werden (SPEC-0054 FR-03 bis FR-05, FR-08 bis FR-11). Ziel ist, dass zwei Implementierungen bei
gleichen Eingaben denselben Report liefern und dass ausgefallene Messungen den Score nie schönen.

## Garantien

Die Szenarien im Artifact
(`.sdd/contracts/behavior/score-berechnung-normierung-gewichtung-n-a-semantik-und-gates.feature`) sind
**ausführbare Spezifikation**. Jedes Szenario MUSS durch einen automatisierten Test (pytest)
abgedeckt sein.

## Formeln

| Größe | Definition |
|-------|------------|
| Normierung | `good < bad`: `n = (bad − roh) / (bad − good)`; `good > bad`: `n = (roh − bad) / (good − bad)`; jeweils auf [0, 1] begrenzt |
| Eingebaute Normierungen (Default, überschreibbar) | `lint_per_kloc` 0→10, `type_errors` 0→20, `suppressions` 0→10, `test_ratio` 1.0→0.0 |
| Innerer Knoten | `Σ wᵢ·sᵢ / Σ wᵢ` über Kinder mit `sᵢ ≠ null` und `wᵢ > 0`; ist diese Menge leer: `null`; `renormalized = true`, wenn ein Kind mit `wᵢ > 0` `null` ist |
| Gewichte Wurzel (Default) | requirements 0,5 · architecture 0,25 · code_quality 0,25 · judge 0 |
| Gewichte in `code_quality` | je Metrik 1, überschreibbar mit `quality.weights.code_quality.<metrik>` |
| requirements | `fr = #erfüllt / #FR`; mit Holdout: `0,5·fr + 0,5·holdout_pass_rate`; `null`, wenn ein FR `unbekannt` ist oder die Spec keine FRs hat |
| architecture | `1 − min(1, Σ gewicht / threshold)` mit `error` = 1,0, `warn` = 0,25 (Baseline-Treffer zählen als `warn`); `threshold` = `quality.architecture.threshold`, Default 5; `null`, wenn die Sonde `deps` ausgefallen ist, keine Regeln existieren oder mehr als die Hälfte der Regeln `n/a` ist |
| architecture.errors | Anzahl der Verstöße mit `severity: error` nach Baseline-Herabstufung |
| Rundung | Im Report auf 4 Nachkommastellen; Gates vergleichen ungerundete Werte |

## Invarianten (über alle Szenarien hinweg)

- **INV-01:** `n/a` (`null`) wird nie als 0 behandelt und nie als bestanden gewertet.
- **INV-02:** Renormierung passiert nur zwischen Geschwisterknoten und wird immer sichtbar markiert
  (`renormalized` am Knoten, `incomplete` am Report).
- **INV-03:** Ein Sondenausfall ist genau einer der Fälle: Befehl nicht gefunden, Zeitlimit
  überschritten, keine Ausgabe unter `{out}`, Ausgabe nicht parsebar, Holdout-Pfad verboten. Ein
  Exit-Code ≠ 0 mit gültiger Ausgabe ist kein Ausfall.
- **INV-04:** Gates haben die Form `<pfad> <op> <zahl>` mit `pfad` ∈ {`total`, `requirements`,
  `architecture`, `code_quality`, `judge`, `architecture.errors`} und `op` ∈ {`>=`, `>`, `<=`, `<`,
  `==`}. Ein Gate auf einen `null`-Wert ist **nicht bestanden** (fail-closed).
- **INV-05:** Bei gleichen Sondenausgaben und gleicher Konfiguration ist der Report bis auf
  `generated_at`, `duration_ms` und die Sondenlaufzeiten identisch.
- **INV-06:** Ein FR-Status wird aus der Vereinigung aller Zuordnungsquellen bestimmt. Übersprungene
  Testfälle (`skipped`) zählen weder als grün noch als rot. Ein FR nur mit übersprungenen Testfällen
  ist `fehlt`.

## Begriffe

| Begriff | Definition |
|---------|------------|
| Sonde | Befehl aus `quality.yaml`, der ein Austauschformat erzeugt (CON-0192) |
| Sondenausfall | Einer der Fälle aus INV-03; Ergebnis `n/a` mit Grund |
| n/a | Kein Messwert; im Report `null` mit `reason` |
| Renormierung | Neuverteilung der Gewichte auf die vorhandenen Geschwister |
| fail-closed | Fehlender Wert gilt bei einer Schwelle als nicht bestanden |
