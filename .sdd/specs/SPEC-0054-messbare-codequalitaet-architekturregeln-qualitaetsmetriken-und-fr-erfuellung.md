---
id: SPEC-0054
title: "Messbare Codequalität: Architekturregeln, Qualitätsmetriken und FR-Erfüllung"
type: feature
status: draft
owner: "Boris"
created: 2026-09-25
updated: 2026-09-25
version: 0.1.0
priority: high
tags: [quality, architecture, metrics, compliance, gate]
depends_on: [SPEC-0015, SPEC-0041]
contracts: []
tests: []
---

# Messbare Codequalität: Architekturregeln, Qualitätsmetriken und FR-Erfüllung

> **Status:** draft · **Owner:** Boris · **Version:** 0.1.0

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

## 2. Zielsetzung

**Primärziel:** Ein deterministischer Befehl misst für einen Codestand (oder einen Diff) die drei
Qualitätsdimensionen und liefert Einzelmetriken, normierte Teilscores und einen Gesamtscore als
maschinenlesbaren Report.

**Erfolgskriterien (messbar):**
- [ ] `sdd quality measure` liefert für denselben Codestand bei zwei Läufen identische Werte
      (ohne den optionalen LLM-Judge).
- [ ] Architekturregeln aus `.sdd/architecture.yaml` erkennen einen absichtlich eingebauten
      Schichtverstoß in sdd-framer (z. B. `tool/sdd_cli/web` importiert eine verbotene
      Schreibfunktion) mit Datei und Zeile.
- [ ] Der FR-Erfüllungsgrad einer Spec basiert auf **ausgeführten** Tests je FR, nicht nur auf der
      Zuordnung.
- [ ] Laufzeit für sdd-framer (≈ 60 kLOC) ohne Mutationstests und ohne Testlauf: unter 60 s.

**Nicht-Ziele (explizit):**
- Keine automatischen Fixes (`ruff --fix` o. Ä.).
- Kein Ersatz für `sdd validate`; die Artefaktprüfung bleibt dort.
- In dieser Spec nur ein Sprachadapter (Python); Rust und TypeScript folgen als eigene Specs.

## 3. Architektur & Design Patterns

### Strategy: Sprachadapter
`LanguageAnalyzer` (Python in dieser Spec) kapselt Import-Extraktion, Linter, Typprüfer,
Komplexitätsmessung und Testrunner. Der Adapter wird aus `test_languages.py` bzw. der
Projektsprache gewählt.

### Specification Pattern: Architekturregeln
Jede Regel in `.sdd/architecture.yaml` ist eine Specification, die auf einem Import-Graphen oder
einem Aufrufindex ausgewertet wird:

```yaml
version: 1
layers:
  web:      ["tool/sdd_cli/web/**"]
  cli:      ["tool/sdd_cli/main.py", "tool/sdd_cli/*.py"]
  llm:      ["tool/sdd_cli/llm/**"]
rules:
  - id: ARCH-01
    description: "Web-Schicht schreibt keine Artefakte, sie ruft die CLI-Schicht"
    kind: forbidden_import           # forbidden_import | allowed_dependencies | forbidden_call | write_ownership
    from: web
    to: ["tool/sdd_cli/templates.py", "tool/sdd_cli/lifecycle.py:_write_*"]
  - id: ARCH-02
    kind: forbidden_call
    in: ["llm", "web"]
    calls: ["subprocess.run", "subprocess.Popen"]
    except: ["tool/sdd_cli/llm/providers/claude_cli.py"]
  - id: ARCH-03
    kind: write_ownership
    paths: [".sdd/specs/**", ".sdd/contracts/**"]
    owners: ["cli"]
```

Taste Invariants in AGENTS.md können eine Regel referenzieren (`[ARCH-01]`). `sdd validate` meldet
Invarianten ohne maschinelle Regel als Hinweis.

### Composite: Score-Baum
`QualityScore` besteht aus `requirements`, `architecture` und `code_quality`. Jeder Knoten hat
Einzelmetriken, eine Normierung auf 0–1 und ein Gewicht. Gewichte und Schwellen stehen in
`config.yaml` unter `quality:`.

## 4. Funktionale Anforderungen

- **FR-01:** `sdd quality measure [--spec SPEC-XXXX] [--diff BASE_REF] [--json] [--out PFAD]`
  misst den aktuellen Arbeitsstand. Mit `--diff` fließen nur geänderte und neue Dateien in die
  Code- und Architekturmetriken ein, und der Report enthält das Delta gegenüber `BASE_REF`.
- **FR-02:** **Anforderungserfüllung.** Für eine Spec ermittelt der Befehl je FR die zugeordneten
  Tests aus drei Quellen: `fr_test_map`, `Task.fr_ids` (SPEC-0053) und Testmarker
  (`@pytest.mark.fr("FR-03")` bzw. `# FR: FR-03` im Test-Docstring). Er führt die Tests aus und
  setzt den FR-Status:
  - `erfüllt`: alle Tests des FR sind grün.
  - `teilweise`: mindestens einer ist grün.
  - `fehlt`: kein Test zugeordnet oder keiner grün.

  Teilscore = Anteil `erfüllt`. Contract-Coverage aus `test_runner.py` geht als Nebenmetrik ein.
- **FR-03:** Holdout-Ergebnisse (bestehender `holdout_runner`/Evaluator) fließen, sofern vorhanden,
  als Metrik `holdout_pass_rate` in den Anforderungs-Teilscore ein (Default-Gewicht 0,5 innerhalb
  des Teilscores). Der Befehl liest dafür nur die Ergebnisdateien, nie `.sdd/holdout/`.
- **FR-04:** **Architekturtreue.** `.sdd/architecture.yaml` wird gegen
  `contracts/data/architecture-rules.schema.json` validiert. Unterstützte Regelarten:
  - `forbidden_import`
  - `allowed_dependencies` (Schicht-DAG)
  - `forbidden_call`
  - `write_ownership`: Aufrufe von `open(..., "w")`, `Path.write_text`, `os.replace` u. a. mit
    Pfadliteral oder Konstante, die auf ein geschütztes Muster passt.

  Jeder Verstoß wird mit Regel-ID, Datei, Zeile und Auszug gemeldet.
  Teilscore = `1 - min(1, verstöße_gewichtet / schwelle)`, mit Gewichten nach `severity`
  (`error` 1,0; `warn` 0,25).
- **FR-05:** `sdd arch check [--json]` führt nur die Architekturregeln aus und endet mit Exit-Code 1
  bei `error`-Verstößen. `sdd arch init` erzeugt aus der Verzeichnisstruktur und AGENTS.md einen
  Vorschlag für `architecture.yaml` (Schichten nach Top-Level-Paketen, ohne Regeln); Regeln werden
  von Hand ergänzt.
- **FR-06:** **Codequalität.** Der Python-Adapter misst:
  - `lint_per_kloc`: Ruff-Befunde je 1000 Zeilen, mit der Ruff-Konfiguration des Projekts.
  - `type_errors`: Fehler aus `mypy` oder `pyright`, je nachdem, was konfiguriert ist; fehlt beides,
    entfällt die Metrik und wird im Report als `n/a` geführt.
  - `suppressions`: Zahl der `noqa`, `type: ignore` und `pragma: no cover`.
  - `complexity`: mittlere und maximale zyklomatische Komplexität, Anteil der Funktionen > 10.
  - `long_functions`: Anteil der Funktionen > 60 Zeilen.
  - `duplication`: Anteil duplizierter Blöcke ≥ 8 Zeilen (tokenbasiert).
  - `test_ratio`: Testzeilen je Produktionszeile im Diff.

  Jede Metrik hat eine konfigurierbare Normierung (`gut`/`schlecht`-Schwelle, linear dazwischen).
- **FR-07:** Optional (`--mutation`): Mutationsscore der zu einer Spec gehörenden Tests auf den
  geänderten Dateien (mutmut, zeitbegrenzt über `quality.mutation.timeout_seconds`). Die Metrik
  misst die Testqualität und fließt in den Codequalitäts-Teilscore ein, wenn sie vorhanden ist.
- **FR-08:** Optional (`--judge`): Ein LLM-Judge bewertet den Diff anhand einer versionierten
  Rubrik `.sdd/roles/judge.md` (Lesbarkeit, Idiomatik, Passung zum bestehenden Code,
  Fehlerbehandlung; je 1–5 mit Ankerbeschreibungen). Das Ergebnis erscheint als eigener Knoten
  `judge` mit Modell und Rubrikversion und geht **nicht** in den deterministischen Gesamtscore ein,
  außer `quality.weights.judge > 0` ist gesetzt.
- **FR-09:** Der Report folgt `contracts/data/quality-report.schema.json`. Er enthält Metriken,
  Normierung, Teilscores, Gesamtscore, alle Befunde (Datei, Zeile, Regel), Toolversionen,
  Git-SHA und Laufzeit. Mit `--out` wird er als JSON geschrieben, sonst als Rich-Tabelle
  ausgegeben.
- **FR-10:** `quality.gates` in `config.yaml` definiert Schwellen, z. B.
  `requirements >= 1.0`, `architecture.errors == 0`, `code_quality >= 0.7`. Sie werden als
  Gate-Handler für SPEC-0053 (Gates nach `implementer` und Abschluss) sowie optional in
  `sdd finalize` (`quality.gates.on_finalize: warn|block|off`, Default `warn`) genutzt.
- **FR-11:** Fehlt ein externes Werkzeug (ruff, mypy, mutmut), fällt nur die Metrik mit `n/a` und
  Hinweis aus; der Gesamtscore wird über die vorhandenen Metriken renormiert, und der Report weist
  das aus.

## 5. Nicht-funktionale Anforderungen

| Kategorie       | Anforderung                                                               |
|-----------------|---------------------------------------------------------------------------|
| Determinismus   | Ohne `--judge` sind die Ergebnisse bei gleichem Codestand und gleichen Toolversionen identisch. |
| Performance     | Ohne Testlauf, `--mutation` und `--judge` unter 60 s für 60 kLOC. Import-Graph wird pro Git-SHA gecacht. |
| Isolation       | Messung schreibt nur nach `--out` oder `.sdd/quality/`; Holdout-Dateien werden nie gelesen. |
| Erweiterbarkeit | Neue Sprache = neuer `LanguageAnalyzer`, ohne Änderung an Score-Baum oder Report-Schema. |

## 6. Akzeptanzkriterien (Gherkin)

```gherkin
Feature: Qualitätsmessung

  Scenario: Architekturverstoß wird gefunden
    Given architecture.yaml verbietet Importe von "web" nach "tool/sdd_cli/templates.py"
    And tool/sdd_cli/web/api/routes/x.py importiert templates
    When ich "sdd arch check" ausführe
    Then ist der Exit-Code 1
    And die Ausgabe enthält "ARCH-01" mit Datei und Zeile

  Scenario: FR-Erfüllung basiert auf ausgeführten Tests
    Given FR-02 der Spec ist über @pytest.mark.fr("FR-02") zwei Tests zugeordnet
    And einer der Tests schlägt fehl
    When ich "sdd quality measure --spec SPEC-0900 --json" ausführe
    Then hat FR-02 den Status "teilweise"
    And requirements.score ist kleiner als 1.0

  Scenario: Fehlendes Werkzeug
    Given mypy ist nicht installiert
    When ich "sdd quality measure" ausführe
    Then ist type_errors "n/a"
    And der Gesamtscore wird ohne type_errors berechnet und als renormiert markiert
```

## 7. Edge Cases & Fehlerfälle

- Dynamische Importe (`importlib.import_module(variable)`) sind nicht auflösbar und werden als
  `unresolved` gezählt, nicht als Verstoß.
- Lokale Importe in Funktionen (in sdd-framer häufig, z. B. `from .llm.factory import …`) zählen
  wie Modulimporte.
- `write_ownership` mit berechnetem Pfad: nur prüfbar, wenn ein Literal oder eine Modulkonstante
  auflösbar ist; sonst `unresolved` mit Hinweis.
- Spec ohne einen einzigen zugeordneten Test: Anforderungs-Teilscore 0, klarer Hinweis
  „keine FR-Zuordnung“.
- Testlauf hängt: Zeitlimit aus `llm.test_generation_timeout` bzw. `quality.test_timeout_seconds`,
  betroffene FRs werden als `fehlt (timeout)` geführt.

## 8. Contracts (was wird garantiert)

| Contract-ID | Typ      | Was wird garantiert?                                          |
|-------------|----------|---------------------------------------------------------------|
| CON-XXXX    | data     | `architecture-rules.schema.json`                              |
| CON-XXXX    | data     | `quality-report.schema.json` (Metriken, Scores, Befunde)       |
| CON-XXXX    | behavior | CLI `sdd quality measure`, `sdd arch check`, `sdd arch init`  |
| CON-XXXX    | behavior | Normierung und Gewichtung (Formeln, Renormierung bei `n/a`)   |

## 9. Tests (wie wird verifiziert)

| Test-ID  | Level       | Was prüft der Test?                                               |
|----------|-------------|-------------------------------------------------------------------|
| TST-XXXX | unit        | Import-Graph, jede Regelart mit Positiv- und Negativfall          |
| TST-XXXX | unit        | Normierung, Gewichtung, Renormierung                              |
| TST-XXXX | integration | Fixture-Projekt mit bekannten Verstößen und FR-Markern → erwarteter Report (Snapshot) |
| TST-XXXX | acceptance  | Gherkin-Szenarien aus Abschnitt 6                                 |

## 10. Offene Fragen

- [ ] Default-Gewichte des Gesamtscores? Vorschlag: Anforderungen 0,5, Architektur 0,25,
      Codequalität 0,25.
- [ ] Soll der Rust-Adapter (clippy, `cargo metadata` für Crate-Grenzen, `use`-Pfade) direkt
      folgen, damit sddit als zweites Benchmark-Projekt dienen kann?
- [ ] Soll sdd-framer selbst eine `architecture.yaml` bekommen (Dogfooding), und welche
      AGENTS.md-Invarianten sollen zuerst maschinell werden?

## 11. Änderungshistorie

| Datum      | Version | Autor         | Änderung            |
|------------|---------|---------------|---------------------|
| 2026-09-25 | 0.1.0   | Boris, Claude | Initiale Erstellung |
