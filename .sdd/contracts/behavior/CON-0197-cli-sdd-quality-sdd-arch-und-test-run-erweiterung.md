---
id: CON-0197
title: "CLI sdd quality, sdd arch und Test-Run-Erweiterung"
type: behavior
format: gherkin
spec: SPEC-0054
version: 0.3.0
status: approved
artifact: ".sdd/contracts/behavior/cli-sdd-quality-sdd-arch-und-test-run-erweiterung.feature"
tests: ["TST-0226"]
---

# Contract: CLI sdd quality, sdd arch und Test-Run-Erweiterung

> **Spec:** SPEC-0054 · **Typ:** Verhalten (Gherkin) · **Status:** approved

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
| `sdd arch check` | `--json`, `--write-baseline` | wertet nur die Architekturregeln aus; `--json` gibt das Objekt `architecture` des Reports (CON-0195) aus |
| `sdd arch init` | – | schlägt `architecture.yaml` mit Schichten vor |
| `sdd test run` | unverändert | nutzt die Sonde mit `role: tests`, wenn `quality.yaml` sie definiert |
| `sdd validate` | unverändert | prüft zusätzlich die Verknüpfung Regel ↔ ADR |

## Exit-Codes je Befehl

| Befehl | 0 | 1 | 2 |
|--------|---|---|---|
| `quality measure` | Report erzeugt, alle Gates bestanden oder keine Gates | Report erzeugt, mindestens ein Gate nicht bestanden | Konfigurationsfehler (`quality.yaml` fehlt oder ist ungültig, ungültiges Gate) |
| `quality doctor` | alle Sonden einsatzbereit | mindestens eine Sonde nicht einsatzbereit | Konfigurationsfehler |
| `quality init` | Dateien geschrieben (ggf. als `.new`) | – | unbekanntes Preset |
| `arch check` | keine `error`-Verstöße (Baseline-Treffer zählen nicht) | mindestens ein `error`-Verstoß | `architecture.yaml` fehlt oder ist ungültig |
| `arch init` | Vorschlag geschrieben (ggf. als `.new`) | – | kein Projekt gefunden |
| `validate` | wie bisher; ADR-Verknüpfungsfehler zählen als Fehler (Exit 1), Warnungen nicht | | |

## Invarianten (über alle Szenarien hinweg)

- **INV-01:** `--json` schreibt ausschließlich das JSON-Dokument nach stdout. Meldungen und
  Fortschritt gehen nach stderr.
- **INV-02:** Kein Befehl überschreibt ungefragt eine vorhandene, abweichende Projektdatei. Er legt
  `.new` an und zeigt den Diff. **Ausnahmen** sind ausdrückliche Schreib-Optionen, bei denen das
  Überschreiben der Zweck ist: `--out PFAD` und `--write-baseline`. Sie überschreiben das Ziel und
  melden den Diff auf stderr. `--write-baseline` erhält dabei vorhandene Einträge (CON-0198 INV-05).
- **INV-03:** Kein Befehl und keine Option trägt einen Sprach- oder Werkzeugnamen.
  Sprachspezifisches liegt in Preset-Skripten unter `.sdd/quality/`.
- **INV-04:** `sdd quality measure` und `sdd test run` führen Tests über denselben Code-Pfad aus;
  es gibt keinen zweiten Testausführer.
- **INV-05:** Ohne `.sdd/quality.yaml` verhält sich `sdd test run` exakt wie vor SPEC-0054
  (CON-0017/CON-0018), einschließlich des pytest-Runners und `runner: unsupported`.
- **INV-05a (Run-Report-Erweiterung):** Mit einer Sonde `role: tests` führt `sdd test run` genau
  diese Sonde aus, statt des pytest-Runners aus CON-0018. Die JUnit-Datei liegt als
  `<run-datei>.junit.xml` neben dem Run-JSON. Das Run-JSON behält alle Felder aus CON-0017 und
  bekommt zusätzlich:
  - `junit`: relativer Pfad der JUnit-Datei;
  - `testcases`: Liste mit `name`, `classname`, `status` (`passed|failed|error|skipped`) und
    `frs` (FR-IDs aus der Markierung);
  - `git_sha`: Stand, auf dem der Lauf stattfand (Grundlage für `--reuse-test-run`).

  Die Pass/Fail-Zählung je TST-Dokument aus CON-0017 wird aus den Testfällen abgeleitet
  (Testfall-`classname` bzw. Datei ↔ `artifact` des TST-Dokuments). Die drei Felder sind additive,
  optionale Erweiterungen des Run-Report-Schemas aus CON-0017. Dessen Artefakt wird bei der
  Umsetzung entsprechend ergänzt.
- **INV-05b (Verhältnis zu CON-0018):** CON-0018 beschreibt `sdd test run` **ohne** Testsonde und
  gilt dort unverändert. Mit Testsonde gilt:
  - Die Sonde ersetzt den pytest-Runner vollständig. Es gibt kein `runner: unsupported`; ein
    TST-Artefakt ohne passenden Testfall im JUnit-Ergebnis bekommt den Status `missing`.
  - `runner` im Run-Report ist der Text `probe:<sondenname>` (freier Text, kein Enum).
  - Exit-Codes: 0 alle Testfälle grün; 1 mindestens ein Testfall `failed`/`error`; 2 Spec ohne
    Tests (wie CON-0018) **oder** Sonde ausgefallen (CON-0192 INV-09) bzw. `quality.yaml` ungültig,
    jeweils mit Grund auf stderr.
  - Der Altname `sdd test-run` ist ein Verweis auf `sdd test run` und verhält sich identisch.
- **INV-05c (Build-Befehl):** `orchestrator.build_command` (CON-0016) bleibt unverändert zuständig
  für Build und Tests im Dev-Container von `sdd finalize`. Die Zusammenführung mit der Testsonde ist
  Gegenstand von SPEC-0058, nicht dieses Contracts.
- **INV-06:** Befunde von `sdd arch check` nennen immer Regel-ID, ADR-ID, ADR-Titel, Datei und Zeile.
- **INV-07:** `sdd validate` prüft die Verknüpfung zwischen `architecture.yaml` und ADRs:
  - Fehler: Regel verweist auf ein nicht existierendes ADR; doppelte Regel-ID; Regel referenziert
    eine unbekannte Schicht.
  - Warnung: ADR mit Status `accepted`, dessen `enforced_by` auf eine fehlende Regel zeigt; Regel,
    deren ADR `superseded` oder `deprecated` ist.
  - Hinweis: Taste Invariant in AGENTS.md ohne Verweis `[ARCH-NN]`.
- **INV-08:** Ohne `.sdd/architecture.yaml` verhält sich `sdd validate` exakt wie vor SPEC-0054.
  Die neuen Prüfungen aus INV-07 greifen nur, wenn die Datei existiert.

## Begriffe

| Begriff | Definition |
|---------|------------|
| Preset | Vorlage aus `presets/quality/<name>/` im Blueprint: `quality.yaml` und Hilfsskripte |
| Baseline | `.sdd/quality/arch-baseline.json` mit bekannten Verstößen; Format und Semantik regelt CON-0198 |
| Run-Report | persistiertes Ergebnis von `sdd test run` (SPEC-0006) |
