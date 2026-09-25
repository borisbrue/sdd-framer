---
id: SPEC-0054
title: "Messbare Codequalität: Architekturregeln, Qualitätsmetriken und FR-Erfüllung"
type: feature
status: draft
owner: "Boris"
created: 2026-09-25
updated: 2026-09-25
version: 0.2.0
priority: high
tags: [quality, architecture, metrics, compliance, gate, language-agnostic]
depends_on: [SPEC-0015, SPEC-0041]
contracts: []
tests: []
---

# Messbare Codequalität: Architekturregeln, Qualitätsmetriken und FR-Erfüllung

> **Status:** draft · **Owner:** Boris · **Version:** 0.2.0

## 1. Kontext & Motivation

sdd-framer prüft heute die Qualität der **Artefakte** (Schema, Referenzen, SOLID an Spec-Texten,
FR→Test-Zuordnung in der Frontmatter), aber kaum die des **Codes**:

- Architekturregeln stehen als Prosa in AGENTS.md („CLI ist einziger Schreiber“, Schichten). Nichts
  prüft, ob Importe oder Schreibzugriffe sie einhalten.
- Ruff, Typprüfung und Komplexität sind manuelle Regeln. Nur `validate.py` sucht nach
  `noqa`/`type: ignore`.
- Die FR-Erfüllung wird über `fr_test_map` oder eine Substring-Suche in Task-Beschreibungen
  abgeleitet (`compliance.py:99-130`). Ob die zugeordneten Tests grün sind, fließt nicht ein.
  In `/sdd-implement` ist die Abnahme ein Lesen durch Claude.

Für die Rollen-Pipeline (SPEC-0053) braucht der Supervisor harte Fakten statt Selbstauskünfte. Für
den Modellvergleich (SPEC-0056) braucht es reproduzierbare Zahlen für genau die drei Ziele
**Codequalität**, **Architekturtreue** und **Anforderungserfüllung**.

**Leitprinzip: sdd-framer bleibt unabhängig von der Programmiersprache.** Das Projekt entscheidet
selbst, mit welchen Werkzeugen es testet, lintet und seine Abhängigkeiten analysiert, und entwickelt
das weiter. sdd-framer definiert nur, **in welchen Formaten** diese Werkzeuge ihre Ergebnisse
abliefern, und rechnet daraus Metriken und Scores. Sprachwissen liegt in Presets bzw. Stack-Vorlagen
(SPEC-0057), nicht im Kern.

## 2. Zielsetzung

**Primärziel:** Ein deterministischer Befehl misst für einen Codestand (oder einen Diff) die drei
Qualitätsdimensionen anhand der Werkzeuge, die das Projekt selbst konfiguriert hat. Er liefert
Einzelmetriken, normierte Teilscores und einen Gesamtscore als maschinenlesbaren Report.

**Erfolgskriterien (messbar):**
- [ ] Der Kern von `sdd quality` enthält keine sprachspezifische Logik. Das ist per Test geprüft:
      Kein Modul unter `tool/sdd_cli/quality/core` importiert Sprach- oder Werkzeugnamen, und alle
      Werkzeugaufrufe stammen aus `.sdd/quality.yaml`.
- [ ] Mit dem Preset `python` misst `sdd quality measure` sdd-framer selbst. Zwei Läufe auf demselben
      Codestand liefern identische Werte (ohne den optionalen LLM-Judge).
- [ ] Ein Fixture-Projekt in einer zweiten Sprache (minimal, z. B. ein Shell-Skript als
      „Werkzeug“, das SARIF, JUnit und Abhängigkeitskanten ausgibt) läuft ohne Änderung am Kern
      durch.
- [ ] Architekturregeln erkennen einen absichtlich eingebauten Schichtverstoß in sdd-framer mit
      Datei und Zeile.
- [ ] Der FR-Erfüllungsgrad einer Spec basiert auf **ausgeführten** Tests je FR, nicht nur auf der
      Zuordnung.

**Nicht-Ziele (explizit):**
- Keine automatischen Fixes.
- Kein Ersatz für `sdd validate`; die Artefaktprüfung bleibt dort.
- Keine Presets außer `python` in dieser Spec. Weitere Stacks entstehen über Stack-Vorlagen
  (SPEC-0057) oder im Projekt selbst.
- Kein Installieren von Werkzeugen. sdd prüft nur, ob sie da sind (`sdd quality doctor`).

## 3. Architektur & Design Patterns

### Adapter über Austauschformate statt Sprachadapter
Das Projekt beschreibt in `.sdd/quality.yaml` **Sonden**. Jede Sonde ist ein Befehl, der ein
standardisiertes Format erzeugt. sdd-framer bringt nur Parser für diese Formate mit:

| Format        | Wofür                                   | Typische Erzeuger (Beispiele, nicht Teil von sdd) |
|---------------|-----------------------------------------|---------------------------------------------------|
| `junit`       | Testergebnisse, FR-Zuordnung             | pytest `--junitxml`, cargo-nextest, jest-junit, go-junit-report |
| `sarif`       | Linter- und Typprüfer-Befunde            | ruff, eslint, clippy-sarif, semgrep                |
| `cobertura` / `lcov` | Coverage                          | coverage.py, cargo-llvm-cov, c8                    |
| `sdd-deps`    | Abhängigkeitskanten für Architekturregeln | Python-Extraktor aus dem Preset, dependency-cruiser + Konverter, `go list` + Konverter |
| `sdd-metrics` | beliebige Zahlenmetriken (Komplexität, Duplikate, Mutationsscore …) | lizard, jscpd, mutmut + Konverter |

`sdd-deps` und `sdd-metrics` sind kleine, von sdd definierte JSON-Formate für Dinge, für die es
keinen verbreiteten Standard gibt. Konverter von werkzeugspezifischen Ausgaben liegen im Projekt
bzw. im Preset, nicht im Kern.

→ [Refactoring Guru: Adapter](https://refactoring.guru/design-patterns/adapter)

`.sdd/quality.yaml` (Ausschnitt, Preset `python`):
```yaml
version: 1
preset: python                  # optional; Werte des Presets, lokal überschreibbar
probes:
  tests:
    command: "pytest -q --junitxml={out}"
    format: junit
    fr_marker: property         # property (JUnit <property name="fr">) | name (FR-ID im Testnamen)
  lint:
    command: "ruff check --output-format sarif --output-file {out} {paths}"
    format: sarif
    metric: lint_per_kloc
  types:
    command: "mypy --output json {paths} | sdd-convert mypy-json-to-sarif > {out}"
    format: sarif
    metric: type_errors
  deps:
    command: "sdd arch extract-python {paths} > {out}"   # Preset-Extraktor
    format: sdd-deps
  complexity:
    command: "lizard --xml {paths} | python .sdd/quality/lizard_to_metrics.py > {out}"
    format: sdd-metrics
suppressions:                   # Regex je Dateimuster, zählt Unterdrückungen sprachneutral
  "**/*.py": ['#\s*noqa', '#\s*type:\s*ignore', 'pragma:\s*no cover']
normalization:
  lint_per_kloc: { good: 0, bad: 10 }
  type_errors:   { good: 0, bad: 20 }
```

### Specification Pattern: Architekturregeln auf einem neutralen Graphen
Regeln in `.sdd/architecture.yaml` werden auf den Kanten aus `sdd-deps` ausgewertet. Eine Kante hat
die Form `{from, to, kind: import|call|write, file, line}`. Welche Kantenarten ein Projekt liefern
kann, hängt von seinem Extraktor ab. Eine Regel, deren Kantenart fehlt, gilt als `n/a`, nicht als
erfüllt.

```yaml
version: 1
layers:
  web: ["tool/sdd_cli/web/**"]
  cli: ["tool/sdd_cli/main.py", "tool/sdd_cli/*.py"]
  llm: ["tool/sdd_cli/llm/**"]
rules:
  - id: ARCH-01
    description: "Web-Schicht schreibt keine Artefakte, sie ruft die CLI-Schicht"
    kind: forbidden_dependency    # forbidden_dependency | allowed_dependencies | forbidden_call | write_ownership
    from: web
    to: ["tool/sdd_cli/templates.py"]
    severity: error
  - id: ARCH-02
    kind: forbidden_call
    in: [llm, web]
    calls: ["subprocess.run", "subprocess.Popen"]
    except: ["tool/sdd_cli/llm/providers/claude_cli.py"]
  - id: ARCH-03
    kind: write_ownership
    paths: [".sdd/specs/**", ".sdd/contracts/**"]
    owners: [cli]
```

Taste Invariants in AGENTS.md können eine Regel referenzieren (`[ARCH-01]`). `sdd validate` meldet
Invarianten ohne maschinelle Regel als Hinweis.

### Composite: Score-Baum
`QualityScore` besteht aus `requirements` (Gewicht 0,5), `architecture` (0,25) und `code_quality`
(0,25). Jeder Knoten hat Einzelmetriken, eine Normierung auf 0–1 und ein Gewicht. Gewichte und
Schwellen sind in `config.yaml` unter `quality:` überschreibbar.

## 4. Funktionale Anforderungen

- **FR-01:** `sdd quality measure [--spec SPEC-XXXX] [--diff BASE_REF] [--json] [--out PFAD]`
  führt die in `.sdd/quality.yaml` definierten Sonden aus, parst ihre Ausgaben und berechnet den
  Report. Mit `--diff` fließen nur Befunde in geänderten und neuen Dateien in Code- und
  Architekturmetriken ein (`{paths}` wird auf diese Dateien gesetzt, sofern die Sonde
  `diff_scoped: true` erlaubt), und der Report enthält das Delta gegenüber `BASE_REF`.
- **FR-02:** Der Kern unterstützt die Formate `junit`, `sarif`, `cobertura`, `lcov`, `sdd-deps` und
  `sdd-metrics`. `sdd-deps` und `sdd-metrics` sind als JSON-Schema im Contract festgelegt.
  Sprach- oder Werkzeugwissen enthält der Kern nicht.
- **FR-03:** **Anforderungserfüllung.** Je FR werden die zugeordneten Tests aus `fr_test_map`,
  `Task.fr_ids` (SPEC-0053) und den FR-Markierungen im JUnit-Ergebnis zusammengeführt. Die
  Markierung erfolgt entweder als JUnit-Property `fr` oder als FR-ID im Testnamen (`fr_marker`).
  FR-Status:
  - `erfüllt`: alle Tests des FR sind grün.
  - `teilweise`: mindestens einer ist grün.
  - `fehlt`: kein Test zugeordnet oder keiner grün.

  Teilscore = Anteil `erfüllt`.
- **FR-04:** Holdout-Ergebnisse (bestehender `holdout_runner`/Evaluator) fließen, sofern vorhanden,
  als `holdout_pass_rate` mit Gewicht 0,5 in den Anforderungs-Teilscore ein. Der Befehl liest dafür
  nur Ergebnisdateien, nie `.sdd/holdout/`.
- **FR-05:** **Architekturtreue.** `.sdd/architecture.yaml` wird gegen
  `contracts/data/architecture-rules.schema.json` validiert und auf den `sdd-deps`-Kanten
  ausgewertet. Unterstützte Regelarten:
  - `forbidden_dependency`
  - `allowed_dependencies` (Schicht-DAG)
  - `forbidden_call` (braucht Kantenart `call`)
  - `write_ownership` (braucht Kantenart `write`)

  Jeder Verstoß wird mit Regel-ID, Datei, Zeile und Auszug gemeldet.
  Teilscore = `1 - min(1, verstöße_gewichtet / schwelle)`, mit `error` = 1,0 und `warn` = 0,25.
- **FR-06:** `sdd arch check [--json]` wertet nur die Architekturregeln aus und endet mit
  Exit-Code 1 bei `error`-Verstößen. `sdd arch init` schlägt aus der Verzeichnisstruktur Schichten
  vor, ohne Regeln; die Regeln werden von Hand ergänzt.
- **FR-07:** **Codequalität.** Der Teilscore setzt sich aus den Sonden-Metriken zusammen, die das
  Projekt definiert. Eingebaut und sprachneutral sind nur:
  - `lint_per_kloc`: SARIF-Befunde je 1000 Zeilen der gemessenen Dateien.
  - `type_errors`: Anzahl SARIF-Befunde einer als `metric: type_errors` markierten Sonde.
  - `suppressions`: Treffer der Regex-Muster aus `quality.yaml`.
  - `test_ratio`: Testzeilen je Produktionszeile im Diff. Welche Dateien Tests sind, bestimmt das
    Glob-Muster `test_paths`.

  Alle weiteren Metriken (Komplexität, Duplikate, Mutationsscore, Coverage …) kommen als
  `sdd-metrics` bzw. `cobertura`/`lcov` aus Projekt-Sonden. Jede Metrik braucht eine Normierung
  (`good`/`bad`, linear dazwischen), sonst weist `sdd quality doctor` auf den Fehler hin.
- **FR-08:** Optional (`--judge`): Ein LLM-Judge bewertet den Diff anhand einer versionierten
  Rubrik `.sdd/roles/judge.md` (Lesbarkeit, Idiomatik, Passung zum bestehenden Code,
  Fehlerbehandlung; je 1–5 mit Ankerbeschreibungen). Das Ergebnis erscheint als eigener Knoten
  `judge` mit Modell und Rubrikversion und fließt nur in den Gesamtscore ein, wenn
  `quality.weights.judge > 0` gesetzt ist.
- **FR-09:** Der Report folgt `contracts/data/quality-report.schema.json`. Er enthält Metriken,
  Normierung, Teilscores, Gesamtscore, alle Befunde (Datei, Zeile, Regel), die ausgeführten
  Sondenbefehle mit den gemeldeten Werkzeugversionen (`version_command`), Git-SHA und Laufzeit.
- **FR-10:** `quality.gates` in `config.yaml` definiert Schwellen, z. B. `requirements >= 1.0`,
  `architecture.errors == 0`, `code_quality >= 0.7`. Sie dienen als Gate-Handler für SPEC-0053
  und optional für `sdd finalize` (`quality.gates.on_finalize: warn|block|off`, Default `warn`).
- **FR-11:** Schlägt eine Sonde fehl (Befehl fehlt, Exit-Code ≠ 0 ohne Ausgabe, Ausgabe nicht
  parsebar), fällt nur ihre Metrik mit `n/a` und Grund aus. Der Gesamtscore wird über die
  vorhandenen Metriken renormiert, und der Report weist das aus.
- **FR-12:** `sdd quality doctor` führt jede Sonde einmal auf einer minimalen Dateimenge aus und
  meldet je Sonde: gefunden oder fehlt, Format gültig, Normierung vorhanden, FR-Markierung
  erkannt. `sdd quality init [--preset NAME]` schreibt eine `quality.yaml` aus einem Preset.
- **FR-13:** Das Preset `python` liefert Sonden für pytest (JUnit mit FR-Property über ein
  mitgeliefertes pytest-Plugin `@pytest.mark.fr("FR-03")`), ruff (SARIF), mypy (Konverter nach
  SARIF), einen AST-basierten Abhängigkeitsextraktor `sdd arch extract-python` (Kanten `import`,
  `call`, `write`) und lizard (Komplexität, Konverter nach `sdd-metrics`). Presets liegen im
  Blueprint unter `presets/quality/<name>/` und sind die Keimzelle der Stack-Vorlagen (SPEC-0057).

## 5. Nicht-funktionale Anforderungen

| Kategorie        | Anforderung                                                               |
|------------------|---------------------------------------------------------------------------|
| Sprachneutralität | Kern ohne Sprach- und Werkzeugwissen; neue Sprache = neue Sonden in `quality.yaml`, ohne Änderung an sdd. |
| Determinismus    | Ohne `--judge` sind die Ergebnisse bei gleichem Codestand und gleichen Werkzeugversionen identisch. |
| Performance      | Eigener Overhead (Parsen, Regeln, Scores) unter 5 s für 60 kLOC; Sondenlaufzeit wird je Sonde ausgewiesen. |
| Sicherheit       | Sondenbefehle stammen nur aus der versionierten `quality.yaml`. Sie laufen im Projektverzeichnis bzw. Dev-Container und nie mit Pfaden aus `.sdd/holdout/`. |
| Isolation        | Messung schreibt nur nach `--out` bzw. `.sdd/quality/`.                   |

## 6. Akzeptanzkriterien (Gherkin)

```gherkin
Feature: Qualitätsmessung

  Scenario: Architekturverstoß wird gefunden
    Given architecture.yaml verbietet Abhängigkeiten von "web" nach "tool/sdd_cli/templates.py"
    And tool/sdd_cli/web/api/routes/x.py importiert templates
    When ich "sdd arch check" ausführe
    Then ist der Exit-Code 1
    And die Ausgabe enthält "ARCH-01" mit Datei und Zeile

  Scenario: FR-Erfüllung basiert auf ausgeführten Tests
    Given zwei Tests tragen im JUnit-Ergebnis die Property fr=FR-02
    And einer der Tests schlägt fehl
    When ich "sdd quality measure --spec SPEC-0900 --json" ausführe
    Then hat FR-02 den Status "teilweise"
    And requirements.score ist kleiner als 1.0

  Scenario: Fremde Sprache ohne Kernänderung
    Given ein Fixture-Projekt, dessen Sonden Shell-Skripte sind, die JUnit, SARIF und sdd-deps ausgeben
    When ich "sdd quality measure --spec SPEC-0901" ausführe
    Then enthält der Report requirements, architecture und code_quality mit Werten

  Scenario: Fehlende Sonde
    Given die Sonde "types" verweist auf ein nicht installiertes Werkzeug
    When ich "sdd quality measure" ausführe
    Then ist type_errors "n/a" mit Grund
    And der Gesamtscore ist als renormiert markiert
```

## 7. Edge Cases & Fehlerfälle

- Nicht auflösbare Abhängigkeiten (dynamische Importe, Reflection) liefert der Extraktor als Kanten
  mit `to: null` und `unresolved: true`. Sie werden gezählt, sind aber kein Verstoß.
- `write_ownership` mit berechnetem Pfad: Der Extraktor liefert die Kante nur, wenn er den Pfad
  auflösen kann; sonst `unresolved`.
- Spec ohne einen einzigen zugeordneten Test: Anforderungs-Teilscore 0, Hinweis
  „keine FR-Zuordnung“.
- Testsonde hängt: Zeitlimit `probes.<name>.timeout_seconds` (Default 600). Die betroffenen FRs
  werden als `fehlt (timeout)` geführt.
- SARIF mit Befunden außerhalb der gemessenen Pfade (z. B. vendored Code) werden über `exclude` in
  `quality.yaml` ignoriert und im Report als ausgeschlossen gezählt.

## 8. Contracts (was wird garantiert)

| Contract-ID | Typ      | Was wird garantiert?                                            |
|-------------|----------|-----------------------------------------------------------------|
| CON-XXXX    | data     | `quality-config.schema.json` (`.sdd/quality.yaml`: Sonden, Normierung, Suppressions) |
| CON-XXXX    | data     | `sdd-deps.schema.json` und `sdd-metrics.schema.json`            |
| CON-XXXX    | data     | `architecture-rules.schema.json`                                |
| CON-XXXX    | data     | `quality-report.schema.json`                                    |
| CON-XXXX    | behavior | CLI `sdd quality measure|doctor|init`, `sdd arch check|init|extract-python` |
| CON-XXXX    | behavior | Normierung, Gewichtung, Renormierung bei `n/a`                  |

## 9. Tests (wie wird verifiziert)

| Test-ID  | Level       | Was prüft der Test?                                                 |
|----------|-------------|---------------------------------------------------------------------|
| TST-XXXX | unit        | Parser je Format (JUnit, SARIF, Cobertura, LCOV, sdd-deps, sdd-metrics) |
| TST-XXXX | unit        | Jede Regelart auf synthetischen Kanten, Positiv- und Negativfall    |
| TST-XXXX | unit        | Normierung, Gewichtung, Renormierung                                |
| TST-XXXX | unit        | Kern importiert keine Sprach- oder Werkzeugnamen                     |
| TST-XXXX | integration | Shell-Fixture-Projekt (sprachfremd) und Python-Fixture → Report-Snapshot |
| TST-XXXX | acceptance  | Gherkin-Szenarien aus Abschnitt 6                                   |

## 10. Offene Fragen

- [x] Default-Gewichte → Anforderungen 0,5, Architektur 0,25, Codequalität 0,25 (entschieden
      2026-09-25).
- [x] Rust-Adapter → nicht in dieser Spec. Weitere Sprachen kommen über Sonden bzw.
      Stack-Vorlagen (SPEC-0057) (entschieden 2026-09-25).
- [ ] Soll sdd-framer selbst eine `architecture.yaml` und `quality.yaml` bekommen (Dogfooding),
      und welche AGENTS.md-Invarianten sollen zuerst maschinell werden?
- [ ] Soll die bestehende Suche nach Unterdrückungen in `validate.py` (`noqa`/`type: ignore`) auf
      die Muster aus `quality.yaml` umgestellt werden, damit auch sie sprachneutral wird?

## 11. Änderungshistorie

| Datum      | Version | Autor         | Änderung                                                     |
|------------|---------|---------------|--------------------------------------------------------------|
| 2026-09-25 | 0.1.0   | Boris, Claude | Initiale Erstellung                                          |
| 2026-09-25 | 0.2.0   | Boris, Claude | Sprachneutral: Sonden und Austauschformate statt Sprachadapter; Python als Preset; Gewichte festgelegt |
