---
id: CON-0197
title: "CLI sdd quality, sdd arch und Test-Run-Erweiterung"
type: behavior
format: gherkin
spec: SPEC-0054
version: 0.1.0
status: draft
artifact: ".sdd/contracts/behavior/cli-sdd-quality-sdd-arch-und-test-run-erweiterung.feature"
tests: ["TST-0226"]
---

# Contract: CLI sdd quality, sdd arch und Test-Run-Erweiterung

> **Spec:** SPEC-0054 · **Typ:** Verhalten (Gherkin) · **Status:** draft

## Zweck

Legt die Befehlsoberfläche und ihre Exit-Codes fest: `sdd quality measure|doctor|init`,
`sdd arch check|init`, die Erweiterung von `sdd test run` (SPEC-0006) um die Testsonde und die
ADR-Verknüpfungsprüfung in `sdd validate` (SPEC-0054 FR-01, FR-03, FR-06, FR-07, FR-13, FR-14).

## Garantien

Die Szenarien im Artifact
(`.sdd/contracts/behavior/cli-sdd-quality-sdd-arch-und-test-run-erweiterung.feature`) sind
**ausführbare Spezifikation**. Jedes Szenario MUSS durch einen automatisierten Test
(pytest + click `CliRunner`) abgedeckt sein.

## Befehle

| Befehl | Optionen | Wirkung |
|--------|----------|---------|
| `sdd quality measure` | `--spec ID`, `--diff REF`, `--json`, `--out PFAD`, `--reuse-test-run`, `--judge` | misst und gibt den Report aus (CON-0195) |
| `sdd quality doctor` | `--json` | prüft jede Sonde einmal |
| `sdd quality init` | `--preset NAME` | kopiert ein Preset ins Projekt |
| `sdd arch check` | `--json`, `--write-baseline` | wertet nur die Architekturregeln aus |
| `sdd arch init` | – | schlägt `architecture.yaml` mit Schichten vor |
| `sdd test run` | unverändert | nutzt die Sonde `tests`, wenn `quality.yaml` sie definiert |

## Exit-Codes

| Code | Bedeutung |
|------|-----------|
| 0 | Ergebnis erzeugt; alle konfigurierten Gates bestanden bzw. keine `error`-Verstöße |
| 1 | Ergebnis erzeugt, aber ein Gate ist nicht bestanden, ein `error`-Verstoß liegt vor (`arch check`) oder eine Sonde ist nicht einsatzbereit (`doctor`) |
| 2 | Konfigurationsfehler: Datei fehlt, Schema verletzt, unbekanntes Preset |

## Invarianten (über alle Szenarien hinweg)

- **INV-01:** `--json` schreibt ausschließlich das JSON-Dokument nach stdout. Meldungen und
  Fortschritt gehen nach stderr.
- **INV-02:** Kein Befehl überschreibt eine vorhandene, abweichende Projektdatei. Er legt `.new` an
  und zeigt den Diff.
- **INV-03:** Kein Befehl und keine Option trägt einen Sprach- oder Werkzeugnamen.
  Sprachspezifisches liegt in Preset-Skripten unter `.sdd/quality/`.
- **INV-04:** `sdd quality measure` und `sdd test run` führen Tests über denselben Code-Pfad aus;
  es gibt keinen zweiten Testausführer.
- **INV-05:** Ohne `.sdd/quality.yaml` verhält sich `sdd test run` exakt wie vor SPEC-0054.
- **INV-06:** Befunde von `sdd arch check` nennen immer Regel-ID, ADR-ID, ADR-Titel, Datei und Zeile.

## Begriffe

| Begriff | Definition |
|---------|------------|
| Preset | Vorlage aus `presets/quality/<name>/` im Blueprint: `quality.yaml` und Hilfsskripte |
| Baseline | `.sdd/quality/arch-baseline.json` mit bekannten Verstößen (CON-0194 INV-08) |
| Run-Report | persistiertes Ergebnis von `sdd test run` (SPEC-0006) |
