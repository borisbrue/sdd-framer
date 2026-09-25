---
id: SPEC-0054
title: "Messbare Codequalität: Architekturregeln, Qualitätsmetriken und FR-Erfüllung"
type: feature
status: draft
owner: "Boris"
created: 2026-09-25
updated: 2026-09-25
version: 0.5.0
priority: high
tags: [quality, architecture, metrics, compliance, gate, language-agnostic]
depends_on: [SPEC-0006, SPEC-0008, SPEC-0014, SPEC-0015, SPEC-0041]
contracts: [CON-0192, CON-0193, CON-0194, CON-0195, CON-0196, CON-0197]
tests: []
---

# Messbare Codequalität: Architekturregeln, Qualitätsmetriken und FR-Erfüllung

> **Status:** draft · **Owner:** Boris · **Version:** 0.5.0

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
(SPEC-0057), die ins Projekt kopiert werden. Es steckt weder im Kern noch in der Befehlsoberfläche
von `sdd`.

### Abgrenzung zu bestehenden Prüfungen
- **SPEC-0015 (SOLID- und Pattern-Gate):** Diese Prüfung bewertet per LLM Spec- und Contract-Texte
  zur Review-Zeit. Sie fließt **nicht** in den Architekturtreue-Score ein. Architekturtreue misst
  diese Spec ausschließlich deterministisch aus `architecture.yaml` gegen den Code.
- **SPEC-0006 (Test-Runs):** Tests werden nicht auf einem zweiten Weg ausgeführt. `sdd quality
  measure` nutzt den Test-Runner aus SPEC-0006, der dafür erweitert wird (FR-03).
- **SPEC-0014 und SPEC-0004 (Gates):** Der Score erzeugt keine eigene Gate-Logik. Er wird über
  `quality.gates` als zusätzliche Stufe des Qualitäts-Gates aus SPEC-0014 und im `--auto`-Modus
  als Merge-Voraussetzung neben der Holdout-Pass-Rate aus SPEC-0004 genutzt (FR-10).
- Die Einführung im eigenen Repo (Dogfooding) regelt SPEC-0059.

## 2. Zielsetzung

**Primärziel:** Ein deterministischer Befehl misst für einen Codestand (oder einen Diff) die drei
Qualitätsdimensionen anhand der Werkzeuge, die das Projekt selbst konfiguriert hat. Er liefert
Einzelmetriken, normierte Teilscores und einen Gesamtscore als maschinenlesbaren Report.

**Erfolgskriterien (messbar):**
- [ ] Weder der Kern von `sdd quality` noch die `sdd`-CLI enthält sprachspezifische Logik oder
      sprachspezifische Befehle. Das ist per Test geprüft: Kein Modul unter
      `tool/sdd_cli/quality/` und kein CLI-Befehl nennt Sprach- oder Werkzeugnamen. Alle
      Werkzeugaufrufe stammen aus `.sdd/quality.yaml`.
- [ ] Mit dem Preset `python` misst `sdd quality measure` sdd-framer selbst. Zwei Läufe auf demselben
      Codestand liefern identische Werte (ohne den optionalen LLM-Judge).
- [ ] Ein Fixture-Projekt in einer zweiten Sprache (minimal, z. B. ein Shell-Skript als
      „Werkzeug“, das JUnit, SARIF und Abhängigkeitskanten ausgibt) läuft ohne Änderung am Kern
      durch.
- [ ] Architekturregeln erkennen einen absichtlich eingebauten Schichtverstoß in einem
      Fixture-Projekt mit Datei, Zeile und zugehörigem ADR.
- [ ] Der FR-Erfüllungsgrad einer Spec basiert auf **ausgeführten** Tests je FR, nicht nur auf der
      Zuordnung.

**Nicht-Ziele (explizit):**
- Keine automatischen Fixes.
- Kein Ersatz für `sdd validate`; die Artefaktprüfung bleibt dort.
- Keine Presets außer `python` in dieser Spec. Weitere Stacks entstehen über Stack-Vorlagen
  (SPEC-0057) oder im Projekt selbst.
- Kein Installieren von Werkzeugen. sdd prüft nur, ob sie da sind (`sdd quality doctor`).
- Keine Einführung im Repo von sdd-framer selbst (→ SPEC-0059).

## 3. Architektur & Design Patterns

### Template Method: Sonde
Eine **Sonde** ist ein Befehl aus `.sdd/quality.yaml`, der ein Austauschformat erzeugt. Alle Sonden
durchlaufen dasselbe Gerüst `ProbeRun`: Befehl mit Platzhaltern rendern → Pfadsperre prüfen (nie
`.sdd/holdout/`) → mit Timeout ausführen → Ausgabe parsen → Ergebnis oder `n/a` mit Grund
→ Befehl, Werkzeugversion und Laufzeit protokollieren. `measure` und `doctor` überschreiben nur die
variablen Schritte (Dateimenge, Auswertung). Dadurch gilt die Fehlersemantik aus FR-11 für jede
Sonde gleich.

→ [Refactoring Guru: Template Method](https://refactoring.guru/design-patterns/template-method)

### Adapter: ein Parser je Austauschformat
sdd-framer bringt nur Parser für Formate mit, jeweils hinter der Schnittstelle
`ProbeResultParser.parse(path) -> ProbeResult`:

| Format        | Wofür                                   | Typische Erzeuger (Beispiele, nicht Teil von sdd) |
|---------------|-----------------------------------------|---------------------------------------------------|
| `junit`       | Testergebnisse, FR-Zuordnung             | pytest `--junitxml`, cargo-nextest, jest-junit, go-junit-report |
| `sarif`       | Linter- und Typprüfer-Befunde            | ruff, eslint, clippy-sarif, semgrep                |
| `cobertura` / `lcov` | Coverage                          | coverage.py, cargo-llvm-cov, c8                    |
| `sdd-deps`    | Abhängigkeitskanten für Architekturregeln | Extraktor-Skript aus dem Preset, dependency-cruiser + Konverter |
| `sdd-metrics` | beliebige Zahlenmetriken                 | lizard, jscpd, mutmut + Konverter                  |
| `sdd-findings` | beliebige Befunde mit Datei/Zeile/Regel | jedes Werkzeug ohne SARIF + Konverter              |

**Offen für Erweiterung:** `sdd-metrics` und `sdd-findings` sind die universellen Auffangformate.
Jedes Werkzeug, das keines der Standardformate liefert, erreicht den Kern über einen kleinen
Konverter im Projekt. Ein neues Werkzeug oder eine neue Sprache braucht also **nie** eine Änderung am
Kern. Neue Parser für weitere Standardformate (z. B. `checkstyle`) sind eine bewusste, seltene
Kernänderung.

→ [Refactoring Guru: Adapter](https://refactoring.guru/design-patterns/adapter)

`.sdd/quality.yaml` (Ausschnitt, Preset `python`):
```yaml
version: 1
preset: python                  # Herkunft; die Dateien liegen danach im Projekt
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
    command: "mypy --output json {paths} | python .sdd/quality/mypy_to_sarif.py > {out}"
    format: sarif
    metric: type_errors
  deps:
    command: "python .sdd/quality/extract_deps.py {paths} > {out}"
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

### Strategy: eine Strategie je Regelart
Regeln in `.sdd/architecture.yaml` werden auf den Kanten aus `sdd-deps` ausgewertet. Eine Kante hat
die Form `{from, to, kind: import|call|write, file, line}`. Jede Regelart
(`forbidden_dependency`, `allowed_dependencies`, `forbidden_call`, `write_ownership`) ist eine
Strategie mit demselben Vertrag: Sie bekommt Regel und Kanten und liefert alle Verstöße. Sie liefert
`n/a`, wenn die benötigte Kantenart fehlt. Alle Regeln werden unabhängig ausgewertet, und alle
Verstöße werden gesammelt, ohne Kurzschluss.

→ [Refactoring Guru: Strategy](https://refactoring.guru/design-patterns/strategy)

```yaml
version: 1
layers:
  web: ["tool/sdd_cli/web/**"]
  cli: ["tool/sdd_cli/main.py", "tool/sdd_cli/*.py"]
  llm: ["tool/sdd_cli/llm/**"]
rules:
  - id: ARCH-01
    adr: ADR-0007          # „Web-Schicht delegiert jede Schreiboperation an die CLI“
    kind: forbidden_dependency
    from: web
    to: ["tool/sdd_cli/templates.py"]
    severity: error
  - id: ARCH-02
    adr: ADR-0008
    kind: forbidden_call
    in: [llm, web]
    calls: ["subprocess.run", "subprocess.Popen"]
    except: ["tool/sdd_cli/llm/providers/claude_cli.py"]
```

### Entscheidung und Regel: ADR ↔ `architecture.yaml`
Architekturentscheidungen stehen wie bisher als ADR (`sdd new adr`, `docs/adr/`): Kontext, Optionen,
Entscheidung und Begründung, also das **Warum**. `architecture.yaml` enthält nur die maschinell
prüfbare **Folge** einer Entscheidung. Jede Regel verweist auf ihr ADR (`adr:`), und ein ADR listet
in der Frontmatter die Regeln, die es durchsetzen (`enforced_by: [ARCH-01]`). Taste Invariants in
AGENTS.md können eine Regel ebenfalls referenzieren (`[ARCH-01]`).

### Composite: Score-Baum
`QualityScore` besteht aus `requirements` (Gewicht 0,5), `architecture` (0,25) und `code_quality`
(0,25), optional `judge` (Gewicht 0). Blätter sind Metriken, innere Knoten Teilscores. Jeder Knoten
bietet `score()`; Gewichtung und Renormierung bei `n/a` liegen einmal im inneren Knoten und gelten
rekursiv. Der Report ist die Serialisierung dieses Baums. Gewichte und Schwellen sind in
`config.yaml` unter `quality:` überschreibbar.

→ [Refactoring Guru: Composite](https://refactoring.guru/design-patterns/composite)

## 4. Funktionale Anforderungen

- **FR-01:** `sdd quality measure [--spec SPEC-XXXX] [--diff BASE_REF] [--json] [--out PFAD]`
  führt die in `.sdd/quality.yaml` definierten Sonden aus, parst ihre Ausgaben und berechnet den
  Report. Mit `--diff` fließen nur Befunde in geänderten und neuen Dateien in Code- und
  Architekturmetriken ein (`{paths}` wird auf diese Dateien gesetzt, sofern die Sonde
  `diff_scoped: true` erlaubt), und der Report enthält das Delta gegenüber `BASE_REF`.
- **FR-02:** Der Kern unterstützt die Formate `junit`, `sarif`, `cobertura`, `lcov`, `sdd-deps`,
  `sdd-metrics` und `sdd-findings`. Die drei `sdd-*`-Formate sind als JSON-Schema im Contract
  festgelegt. Sprach- oder Werkzeugwissen enthält der Kern nicht.
- **FR-03:** **Anforderungserfüllung.** Tests werden ausschließlich über den Test-Runner aus
  SPEC-0006 ausgeführt. Er wird erweitert: Ist in `quality.yaml` eine Sonde `tests` definiert, führt
  `sdd test run SPEC-XXXX` diese Sonde aus. Er legt das JUnit-Ergebnis neben seinem bisherigen
  Run-Report ab und ergänzt den Report um die einzelnen Testfälle mit Status und FR-Markierung.
  `sdd quality measure --spec` startet diesen Lauf bzw. nutzt mit `--reuse-test-run` den letzten
  Run-Report desselben Git-SHA.
  Je FR werden die Testfälle aus `fr_test_map`, `Task.fr_ids` (SPEC-0053) und den FR-Markierungen
  (JUnit-Property `fr` oder FR-ID im Testnamen, gesteuert über `fr_marker`) zusammengeführt.
  FR-Status:
  - `erfüllt`: alle Testfälle des FR sind grün.
  - `teilweise`: mindestens einer ist grün.
  - `fehlt`: kein Testfall zugeordnet, oder alle zugeordneten sind ausgeführt und rot.
  - `unbekannt`: Die Testsonde ist ausgefallen (FR-11), es gibt also kein Ergebnis.

  Teilscore = Anteil `erfüllt` an allen FRs. Ist mindestens ein FR `unbekannt`, ist der Teilscore
  `n/a`.
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

  Jeder Verstoß wird mit Regel-ID, ADR (ID und Titel), Datei, Zeile und Auszug gemeldet.
  Teilscore = `1 - min(1, verstöße_gewichtet / schwelle)`, mit `error` = 1,0 und `warn` = 0,25.
  Regeln mit Ergebnis `n/a` zählen nicht als erfüllt. Ist mehr als die Hälfte der Regeln `n/a`,
  ist der Teilscore `n/a`.
- **FR-06:** Jede Regel in `architecture.yaml` hat ein Pflichtfeld `adr`. `sdd validate` prüft die
  Verknüpfung in beide Richtungen:
  - Fehler: Regel verweist auf ein nicht existierendes ADR.
  - Warnung: ADR mit Status `accepted`, dessen `enforced_by` auf eine fehlende Regel zeigt.
  - Warnung: Regel, deren ADR `superseded` oder `deprecated` ist.
  - Hinweis: Taste Invariants in AGENTS.md ohne maschinelle Regel.

  Das ADR-Template bekommt das optionale Feld `enforced_by`.
- **FR-07:** `sdd arch check [--json]` wertet nur die Architekturregeln aus und endet mit
  Exit-Code 1 bei `error`-Verstößen. Eine optionale Baseline `.sdd/quality/arch-baseline.json`
  listet bekannte Verstöße (Regel-ID, Datei, Symbol, Grund, behebende Spec). Passen Regel, Datei und
  Symbol, wird ein Verstoß auf `warn` herabgestuft. Neue Verstöße bleiben `error`. Nicht mehr
  vorkommende Einträge werden als „Baseline kann bereinigt werden“ gemeldet.
  `sdd arch check --write-baseline` erzeugt die Baseline aus dem aktuellen Stand. `sdd arch init` schlägt aus der Verzeichnisstruktur Schichten
  vor, ohne Regeln; die Regeln werden von Hand ergänzt.
- **FR-08:** **Codequalität.** Der Teilscore setzt sich aus den Sonden-Metriken zusammen, die das
  Projekt definiert. Eingebaut und sprachneutral sind nur:
  - `lint_per_kloc`: SARIF- bzw. `sdd-findings`-Befunde je 1000 Zeilen der gemessenen Dateien.
  - `type_errors`: Anzahl Befunde einer als `metric: type_errors` markierten Sonde.
  - `suppressions`: Treffer der Regex-Muster aus `quality.yaml`.
  - `test_ratio`: Testzeilen je Produktionszeile im Diff. Welche Dateien Tests sind, bestimmt das
    Glob-Muster `test_paths`.

  Alle weiteren Metriken (Komplexität, Duplikate, Mutationsscore, Coverage …) kommen als
  `sdd-metrics` bzw. `cobertura`/`lcov` aus Projekt-Sonden. Jede Metrik braucht eine Normierung
  (`good`/`bad`, linear dazwischen), sonst weist `sdd quality doctor` auf den Fehler hin.
- **FR-09:** Optional (`--judge`): Ein LLM-Judge bewertet den Diff anhand einer versionierten
  Rubrik `.sdd/roles/judge.md` (Lesbarkeit, Idiomatik, Passung zum bestehenden Code,
  Fehlerbehandlung; je 1–5 mit Ankerbeschreibungen). Der Aufruf läuft über die Provider-Factory aus
  SPEC-0008 (`llm.roles.judge`, Default `claude-cli`), damit kein lokal getestetes Modell seine
  eigene Arbeit bewertet. Das Ergebnis erscheint als eigener Knoten `judge` mit Modell und
  Rubrikversion. Es fließt nur in den Gesamtscore ein, wenn `quality.weights.judge > 0` gesetzt ist.
- **FR-10:** `quality.gates` in `config.yaml` definiert Schwellen, z. B. `requirements >= 1.0`,
  `architecture.errors == 0`, `code_quality >= 0.7`. Die Gates sind **fail-closed**: Ein Teilscore
  `n/a` in einer Dimension mit Schwelle gilt als nicht bestanden. Verwendet werden sie:
  - als Gate-Handler für SPEC-0053 (nach `implementer` und zum Abschluss);
  - als zusätzliche Stufe des Qualitäts-Gates aus SPEC-0014;
  - im `--auto`-Modus der Pipeline als Merge-Voraussetzung neben der Holdout-Pass-Rate aus SPEC-0004;
  - optional in `sdd finalize` (`quality.gates.on_finalize: warn|block|off`, Default `warn`).
- **FR-11:** **Einheitliche Fehlersemantik für alle Sonden.** Fällt eine Sonde aus (Befehl fehlt,
  Timeout, Exit-Code ≠ 0 ohne verwertbare Ausgabe, Ausgabe nicht parsebar), ist ihr Ergebnis `n/a`
  mit Grund, gleich welche Sonde es ist. Folgen:
  - Metriken der Sonde sind `n/a`.
  - Bei der Testsonde werden die betroffenen FRs `unbekannt` (FR-03).
  - Innere Knoten renormieren über ihre vorhandenen Kinder. Ein Teilscore, dessen Kinder alle
    `n/a` sind, ist selbst `n/a`.
  - Der Gesamtscore wird über die vorhandenen Teilscores renormiert und als `incomplete` markiert.

  Ein Exit-Code ≠ 0 **mit** gültiger Ausgabe (z. B. Linter mit Befunden, Tests mit Fehlschlägen)
  ist kein Ausfall.
- **FR-12:** Der Report folgt `contracts/data/quality-report.schema.json`. Er enthält:
  - Metriken und Normierung,
  - Teilscores und Gesamtscore samt `incomplete`-Markierung,
  - alle Befunde (Datei, Zeile, Regel, ADR),
  - die ausgeführten Sondenbefehle mit Werkzeugversionen (`version_command`),
  - Git-SHA und Laufzeit.
- **FR-13:** `sdd quality doctor` führt jede Sonde einmal auf einer minimalen Dateimenge aus und
  meldet je Sonde: gefunden oder fehlt, Format gültig, Normierung vorhanden, FR-Markierung
  erkannt. `sdd quality init [--preset NAME]` kopiert ein Preset ins Projekt: `quality.yaml` und
  alle Hilfsskripte nach `.sdd/quality/`. Gibt es die Dateien schon, entsteht `.new` mit Diff, wie
  bei `sdd upgrade`.
- **FR-14:** Das Preset `python` liegt im Blueprint unter `presets/quality/python/` und enthält:
  - Sonden für pytest (JUnit mit FR-Property über ein mitgeliefertes pytest-Plugin
    `@pytest.mark.fr("FR-03")`), ruff (SARIF), mypy mit Konverter-Skript nach SARIF und lizard mit
    Konverter-Skript nach `sdd-metrics`;
  - einen AST-basierten Abhängigkeitsextraktor als Skript `extract_deps.py` (Kanten `import`,
    `call`, `write`).

  Alle Skripte werden ins Projekt kopiert und dort aufgerufen. `sdd` bietet dafür **keine**
  eigenen Unterbefehle an. Presets sind die Keimzelle der Stack-Vorlagen (SPEC-0057).

## 5. Nicht-funktionale Anforderungen

| Kategorie        | Anforderung                                                               |
|------------------|---------------------------------------------------------------------------|
| Sprachneutralität | Kern und CLI ohne Sprach- und Werkzeugwissen; neue Sprache = neue Sonden und Skripte im Projekt, ohne Änderung an sdd. |
| Determinismus    | Ohne `--judge` sind die Ergebnisse bei gleichem Codestand und gleichen Werkzeugversionen identisch. |
| Performance      | Eigener Overhead (Parsen, Regeln, Scores) unter 5 s für 60 kLOC; Sondenlaufzeit wird je Sonde ausgewiesen. |
| Sicherheit       | Sondenbefehle stammen nur aus der versionierten `quality.yaml`. Sie laufen im Projektverzeichnis bzw. Dev-Container und nie mit Pfaden aus `.sdd/holdout/`. |
| Isolation        | Messung schreibt nur nach `--out`, `.sdd/quality/runs/` und in die Test-Run-Ablage aus SPEC-0006. |

## 6. Akzeptanzkriterien (Gherkin)

```gherkin
Feature: Qualitätsmessung

  Scenario: Architekturverstoß wird mit ADR gemeldet
    Given architecture.yaml enthält Regel ARCH-01 mit adr ADR-0007, die Abhängigkeiten von "web" nach "core/writer.py" verbietet
    And web/routes.py importiert core/writer.py
    When ich "sdd arch check" ausführe
    Then ist der Exit-Code 1
    And die Ausgabe enthält "ARCH-01", "ADR-0007", Datei und Zeile

  Scenario: FR-Erfüllung basiert auf ausgeführten Tests
    Given zwei Testfälle tragen im JUnit-Ergebnis die Property fr=FR-02
    And einer der Testfälle schlägt fehl
    When ich "sdd quality measure --spec SPEC-0900 --json" ausführe
    Then hat FR-02 den Status "teilweise"
    And requirements.score ist kleiner als 1.0

  Scenario: Ausgefallene Testsonde wird nicht schöngerechnet
    Given die Sonde "tests" bricht ohne JUnit-Ausgabe ab
    When ich "sdd quality measure --spec SPEC-0900 --json" ausführe
    Then haben alle FRs den Status "unbekannt"
    And requirements.score ist "n/a"
    And der Report ist als "incomplete" markiert
    And ein Gate "requirements >= 1.0" gilt als nicht bestanden

  Scenario: Fremde Sprache ohne Kernänderung
    Given ein Fixture-Projekt, dessen Sonden Shell-Skripte sind, die JUnit, sdd-findings und sdd-deps ausgeben
    When ich "sdd quality measure --spec SPEC-0901" ausführe
    Then enthält der Report requirements, architecture und code_quality mit Werten

  Scenario: Fehlendes Werkzeug
    Given die Sonde "types" verweist auf ein nicht installiertes Werkzeug
    When ich "sdd quality measure" ausführe
    Then ist type_errors "n/a" mit Grund
    And code_quality wird über die übrigen Metriken renormiert
```

## 7. Edge Cases & Fehlerfälle

- Nicht auflösbare Abhängigkeiten (dynamische Importe, Reflection) liefert der Extraktor als Kanten
  mit `to: null` und `unresolved: true`. Sie werden gezählt, sind aber kein Verstoß.
- `write_ownership` mit berechnetem Pfad: Der Extraktor liefert die Kante nur, wenn er den Pfad
  auflösen kann; sonst `unresolved`.
- Spec ohne einen einzigen zugeordneten Test: alle FRs `fehlt`, Teilscore 0, Hinweis
  „keine FR-Zuordnung“.
- Testsonde hängt: Timeout `probes.<name>.timeout_seconds` (Default 600) → Ausfall nach FR-11,
  also FRs `unbekannt`.
- SARIF mit Befunden außerhalb der gemessenen Pfade (z. B. vendored Code) wird über `exclude` in
  `quality.yaml` ignoriert und im Report als ausgeschlossen gezählt.
- Projekt ohne `quality.yaml`: `sdd quality measure` bricht mit Hinweis auf `sdd quality init` ab.
  `sdd test run` verhält sich wie bisher (SPEC-0006).

## 8. Contracts (was wird garantiert)

| Contract-ID | Typ      | Was wird garantiert?                                            |
|-------------|----------|-----------------------------------------------------------------|
| CON-0192    | data     | `quality-config.schema.json` (`.sdd/quality.yaml`: Sonden, Normierung, Suppressions) |
| CON-0193    | data     | Austauschformate `sdd-deps`, `sdd-metrics`, `sdd-findings`      |
| CON-0194    | data     | `architecture-rules.schema.json` inkl. Pflichtfeld `adr`, `arch-baseline.json` |
| CON-0195    | data     | `quality-report.schema.json`                                    |
| CON-0196    | behavior | Score-Berechnung: Normierung, Gewichtung, einheitliche `n/a`-Semantik, fail-closed Gates |
| CON-0197    | behavior | CLI `sdd quality measure|doctor|init`, `sdd arch check|init`, Erweiterung `sdd test run`, ADR-Prüfung in `sdd validate` |

## 9. Tests (wie wird verifiziert)

| Test-ID  | Level       | Was prüft der Test?                                                 |
|----------|-------------|---------------------------------------------------------------------|
| TST-XXXX | unit        | Parser je Format (JUnit, SARIF, Cobertura, LCOV, sdd-deps, sdd-metrics, sdd-findings) |
| TST-XXXX | unit        | Jede Regelart-Strategie auf synthetischen Kanten, Positiv-, Negativ- und `n/a`-Fall |
| TST-XXXX | unit        | Score-Baum: Normierung, Gewichtung, Renormierung, `incomplete`, fail-closed |
| TST-XXXX | unit        | Kern und CLI nennen keine Sprach- oder Werkzeugnamen                 |
| TST-XXXX | integration | Shell-Fixture-Projekt (sprachfremd) und Python-Fixture → Report-Snapshot |
| TST-XXXX | acceptance  | Gherkin-Szenarien aus Abschnitt 6                                   |

## 10. Offene Fragen

- [x] Default-Gewichte → Anforderungen 0,5, Architektur 0,25, Codequalität 0,25 (entschieden
      2026-09-25).
- [x] Rust-Adapter → nicht in dieser Spec. Weitere Sprachen kommen über Sonden bzw.
      Stack-Vorlagen (SPEC-0057) (entschieden 2026-09-25).
- [x] Dogfooding → ja, ausgelagert nach SPEC-0059 (entschieden 2026-09-25).
- [ ] Soll die bestehende Suche nach Unterdrückungen in `validate.py` (`noqa`/`type: ignore`) auf
      die Muster aus `quality.yaml` umgestellt werden, damit auch sie sprachneutral wird?

## 11. Änderungshistorie

| Datum      | Version | Autor         | Änderung                                                     |
|------------|---------|---------------|--------------------------------------------------------------|
| 2026-09-25 | 0.1.0   | Boris, Claude | Initiale Erstellung                                          |
| 2026-09-25 | 0.2.0   | Boris, Claude | Sprachneutral: Sonden und Austauschformate statt Sprachadapter; Python als Preset; Gewichte festgelegt |
| 2026-09-25 | 0.3.0   | Boris, Claude | Regeln sind an ADRs gebunden (`adr`/`enforced_by`)           |
| 2026-09-25 | 0.4.0   | Boris, Claude | Dogfooding mit Baseline; Claude als Default-Gutachter        |
| 2026-09-25 | 0.5.0   | Boris, Claude | Review: Patterns Template Method/Adapter/Strategy/Composite; einheitliche `n/a`-Semantik und fail-closed Gates; `sdd-findings`; Preset-Skripte statt CLI-Befehle; Tests über `sdd test run` (SPEC-0006); Abgrenzung zu SPEC-0004/0008/0014/0015; Dogfooding → SPEC-0059 |
