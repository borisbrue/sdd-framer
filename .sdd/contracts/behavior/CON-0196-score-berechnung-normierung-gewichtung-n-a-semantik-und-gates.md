---
id: CON-0196
title: "Score-Berechnung: Normierung, Gewichtung, n/a-Semantik und Gates"
type: behavior
format: gherkin
spec: SPEC-0054
version: 0.3.0
status: approved
artifact: ".sdd/contracts/behavior/score-berechnung-normierung-gewichtung-n-a-semantik-und-gates.feature"
tests: ["TST-0225"]
---

# Contract: Score-Berechnung: Normierung, Gewichtung, n/a-Semantik und Gates

> **Spec:** SPEC-0054 · **Typ:** Verhalten (Gherkin) · **Status:** approved

## Zweck

Legt fest, wie aus Sondenergebnissen Metriken, Teilscores, der Gesamtscore und Gate-Entscheidungen
werden (SPEC-0054 FR-03 bis FR-05, FR-08 bis FR-11). Wann eine Sonde ausgefallen ist, regelt
CON-0192 INV-09. Dieser Contract regelt nur die Folgen eines Ausfalls. Ziel ist, dass zwei Implementierungen bei
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
| Innerer Knoten | `Σ wᵢ·sᵢ / Σ wᵢ` über Kinder mit `sᵢ ≠ null` und `wᵢ > 0`; `renormalized = true`, wenn ein Kind mit `wᵢ > 0` `null` ist. Wann der Knoten selbst `null` wird, bestimmt seine n/a-Regel |
| n/a-Regel | `renormalize`: `null` nur, wenn alle gewichteten Kinder `null` sind · `strict`: `null`, sobald ein gewichtetes Kind `null` ist · `quorum(q)`: `null`, wenn der Anteil `null`-Kinder > `q` ist. Defaults: Wurzel und `code_quality` `renormalize`, `requirements` `strict` (Kinder = FRs), `architecture` `quorum(0,5)` (Kinder = Regeln) |
| Gewichte Wurzel (Default) | requirements 0,5 · architecture 0,25 · code_quality 0,25 · judge 0 |
| Gewichte in `code_quality` | je Metrik 1, überschreibbar mit `quality.weights.code_quality.<metrik>` |
| Teilnahme eingebauter Metriken | `lint_per_kloc`/`type_errors` nur, wenn eine Sonde sie per `metric` speist; `suppressions` nur, wenn `suppressions` konfiguriert ist; `test_ratio` nur mit `--diff` und `test_paths`. Eine nicht teilnehmende Metrik erscheint nicht im Baum, auch nicht als `null` |
| `lint_per_kloc` | Befunde (SARIF bzw. `sdd-findings`, ohne Schweregrad `note`) je 1000 Zeilen der gemessenen Dateien (CON-0192 `{paths}`) |
| Ausgefallene Sonde ohne `metric` | erscheint in `code_quality` als Metrik mit dem Sondennamen, `normalized: null` und Grund, damit die Renormierung sichtbar bleibt |
| requirements | `fr = #erfüllt / #FR`; mit Holdout: `(1 − h)·fr + h·holdout_pass_rate`, `h` = `quality.weights.requirements.holdout`, Default 0,5; `null`, wenn ein FR `unbekannt` ist oder die Spec keine FRs hat |
| holdout_pass_rate | aus der jüngsten gültigen Datei unter `.sdd/evaluations/` (Format des Evaluators, CON-0010 G-06 / CON-0162), die Szenarien mit einem `contract` der Spec enthält: `bestanden / (bestanden + nicht bestanden)` unter diesen Szenarien. Übersprungene Szenarien (ein Lauf mit `llm_verdict: "skip"`, fail-fast) und Messfehler (alle Läufe mit `llm_verdict: "error"`, z. B. Abbruch nach CON-0010 G-07) zählen weder im Zähler noch im Nenner; Tiers werden nicht gewichtet. **Ungültig** und ignoriert wird eine Datei, die für die Spec nur übersprungene oder fehlerhafte Szenarien enthält. Gibt es keine gültige Datei, entfällt der Holdout-Anteil (`holdout_pass_rate: null` mit Grund), er zählt nie als 0 |
| Verhältnis zur Auto-Merge-Schwelle | Die feste 90-%-Schwelle aus CON-0010 G-05 bleibt bestehen. Im `--auto`-Modus (SPEC-0053/SPEC-0058) müssen **beide** erfüllt sein: CON-0010 G-05 und alle `quality.gates` |
| architecture | `1 − min(1, Σ gewicht / threshold)`; Gewichte `quality.architecture.severity_weights`, Default `error` 1,0, `warn` 0,25 (Baseline-Treffer zählen als `warn`); `threshold` = `quality.architecture.threshold`, Default 5; `null`, wenn die Sonde mit `role: deps` ausgefallen ist oder fehlt, keine Regeln existieren oder mehr als die Hälfte der Regeln `n/a` ist |
| Zähler | `count.architecture.errors` (Verstöße mit `severity: error` nach Baseline), `count.architecture.warnings`, `count.frs_missing` (FRs mit `fehlt`), `count.probes_na` (ausgefallene Sonden) |
| FR-Status | aus den Testfällen der Sonde mit `role: tests` (siehe Szenarien) |
| Rundung | Im Report auf 4 Nachkommastellen; Gates vergleichen ungerundete Werte |

## Invarianten (über alle Szenarien hinweg)

- **INV-01:** `n/a` (`null`) wird nie als 0 behandelt und nie als bestanden gewertet.
- **INV-02:** Renormierung passiert nur zwischen Geschwisterknoten und wird immer sichtbar markiert
  (`renormalized` am Knoten, `incomplete` am Report).
- **INV-03:** Die Folgen eines Sondenausfalls (CON-0192 INV-09): Metriken der Sonde werden `null`.
  Bei `role: tests` werden alle FRs `unbekannt`, bei `role: deps` wird `architecture` `null`.
- **INV-04:** Gates haben die Form `<pfad> <op> <zahl>` mit `op` ∈ {`>=`, `>`, `<=`, `<`, `==`}.
  Es gibt zwei Arten von Pfaden, die nicht vermischt werden:
  - **Score-Pfade**: `total` oder ein beliebiger Knoten- bzw. Metrikpfad im Baum, z. B.
    `requirements`, `code_quality.lint_per_kloc`. Die Zahl liegt in [0, 1].
  - **Zähler-Pfade**: beginnen mit `count.` (siehe Formeln). Die Zahl ist eine nicht negative
    ganze Zahl.

  Ein Gate mit unbekanntem Pfad, unzulässigem Operator oder falschem Zahlentyp ist ein
  Konfigurationsfehler. Ein Gate auf einen `null`-Wert ist **nicht bestanden** (fail-closed).
- **INV-07 (Konfigurationsprüfung):** `sdd config validate` (CON-0190/CON-0191) bekommt eine
  Regelgruppe `quality`. Mit Level `error` meldet sie:
  - ungültige Gates (Pfad `quality.gates[i]`);
  - negative Gewichte (`quality.weights.…`);
  - `quality.architecture.threshold ≤ 0`;
  - Schemaverstöße einer vorhandenen `.sdd/quality.yaml` gegen CON-0192 (Pfad
    `quality.yaml:<feldpfad>`).

  Die Ausgabe folgt dem Format aus CON-0191 (`{level, path, message}`), der Exit-Code ist 1.
  `sdd quality measure` prüft dieselben Regeln vor dem Messen und endet bei Fehlern mit Exit 2.
- **INV-08 (Beleg im Gate):** Jede Gate-Entscheidung, die auf einem Report beruht, schreibt
  `report_path`, `git_sha` und `schema_version` des Reports als Zusatzfelder in den Gate-Eintrag
  unter `.sdd/pipeline/<SPEC>-gate.json` (additiv zu CON-0030). Ein Report mit unbekannter
  `schema_version` gilt für Gates als nicht bestanden.
- **INV-05:** Bei gleichen Sondenausgaben und gleicher Konfiguration ist der Report bis auf
  `generated_at`, `duration_ms` und die Sondenlaufzeiten identisch.
- **INV-06:** Ein FR-Status wird aus der Vereinigung aller Zuordnungsquellen bestimmt. Übersprungene
  Testfälle (`skipped`) zählen weder als grün noch als rot. Ein FR nur mit übersprungenen Testfällen
  ist `fehlt`.

## Begriffe

| Begriff | Definition |
|---------|------------|
| Sonde | Befehl aus `quality.yaml`, der ein Austauschformat erzeugt (CON-0192) |
| Testsonde / Abhängigkeitssonde | Sonde mit `role: tests` bzw. `role: deps` |
| Sondenausfall | siehe CON-0192 INV-09; Ergebnis `n/a` mit Grund |
| n/a | Kein Messwert; im Report `null` mit `reason` |
| Renormierung | Neuverteilung der Gewichte auf die vorhandenen Geschwister |
| fail-closed | Fehlender Wert gilt bei einer Schwelle als nicht bestanden |
