---
id: SPEC-0063
title: "Benchmark-Suite e2e: Fixture-Projekt mit ganzen Pipeline-Runs"
type: feature
status: approved
owner: "Boris"
created: 2026-09-27
updated: 2026-09-27
version: 0.2.0
priority: high
tags: [benchmark, pipeline, fixture, quality]
depends_on: [SPEC-0056, SPEC-0053, SPEC-0054, SPEC-0061]
contracts:
- CON-0225
- CON-0226
tests:
- TST-0254
- TST-0255
fr_test_map:
  FR-01: [TST-0254]
  FR-02: [TST-0255]
  FR-03: [TST-0255]
  FR-04: [TST-0255]
  FR-05: [TST-0255]
  FR-06: [TST-0255]
  FR-07: [TST-0255]
---

# Benchmark-Suite e2e: Fixture-Projekt mit ganzen Pipeline-Runs

> **Status:** approved · **Owner:** Boris · **Version:** 0.2.0

## 1. Kontext & Motivation

Aus SPEC-0056 abgespalten. SPEC-0056 liefert die Benchmark-Engine mit den Suiten `roles` (einzelne
Rollen) und `regen` (einzelne Module). Beide messen Ausschnitte. Diese Spec ergänzt die
realistischste Stufe: ganze Specs eines Fixture-Projekts per `sdd pipeline run` mit einer
Modellbelegung umsetzen und den Endstand mit versteckten Akzeptanztests und der Qualitätsmessung
(SPEC-0054) bewerten.

Bestand:

| Baustein | Stand | Nutzung hier |
|----------|-------|--------------|
| Benchmark-Engine, Suite-Registry, Records, Report | vorhanden (SPEC-0056) | neue Suite-Art `e2e` |
| `sdd pipeline run --auto --steps` | vorhanden (SPEC-0061, SPEC-0062) | ein Run je Spec, ohne Finalize |
| Usage je Run in `token_usage` (`run_id`, Komponente `role:<rolle>`) | vorhanden (SPEC-0060) | Tokens je Rolle, Budget |
| Budget im Pipeline-Run | fehlt | FR-01 |

## 2. Zielsetzung

**Primärziel:** Suite-Art `e2e` für `sdd bench run` mit dem Fixture `todo-service`, dazu ein
allgemeines Token-Budget für Pipeline-Runs.

**Erfolgskriterien (messbar):**
- [ ] Die Referenzlösung des Fixtures besteht alle versteckten Akzeptanztests, der Startstand keinen.
- [ ] `sdd bench run --suite e2e` erzeugt je Belegung und Wiederholung einen Record mit `q_kind:
      quality`, Teilscores und Tokens je Rolle.
- [ ] Ein Pipeline-Run mit überschrittenem Budget hält mit Grund `budget`; der Record trägt den
      erreichten Stand.

**Nicht-Ziele (explizit):**
- Kein nächtlicher CI-Lauf und keine GitHub-Action.
- Keine Container-Isolation (später als weitere Strategie möglich).
- Keine Änderung an Report-Formeln, Pareto oder `apply-roles` außer der Ausweisung von Ausgängen.

## 3. Architektur & Design Patterns

Angenommen (Review 2026-09-27): **Template Method** (e2e als `BenchTask`), **Proxy** (versteckte
Akzeptanztests und Referenzlösung), **Decorator** (Zählung der Tokens eines Runs), **Strategy**
(Isolationsart).

- **Aufruf der Pipeline:** Der Benchmark startet `sdd pipeline run` als eigenen Prozess im
  Arbeitsverzeichnis. Er greift nicht auf Pipeline-Interna zu (ARCH-05). Die Belegung steht in
  der `config.yaml` der Kopie, nicht im Projekt.
- **Budget:** Das Budget ist ein allgemeines Feature der Pipeline (SRP/DIP-Befund). Der Benchmark
  setzt es nur über Run-Optionen.
- **Isolation:** `WorkspaceStrategy` erzeugt und entfernt Arbeitsverzeichnisse. Die Umsetzung `dir`
  kopiert das Fixture ohne `hidden/` und `reference/` in ein Temp-Verzeichnis und macht es zu einem
  eigenen Git-Repository mit Start-Commit.
- **Fixture im Blueprint:**
  ```
  blueprint/bench/fixtures/todo-service/
  ├── project/     # Startstand: .sdd/ (3 Specs approved, Gates), AGENTS.md, architecture.yaml,
  │                #   quality.yaml, Gerüst der Schichten, sichtbare Tests
  ├── hidden/      # versteckte Akzeptanztests (unittest, FR-Marker im Testnamen)
  └── reference/   # Referenzlösung (Overlay über project/)
  ```
  Suite `bench/suites/e2e.yaml` (`kind: e2e`): `fixture`, `specs` (Reihenfolge), `test_command` der
  Akzeptanztests, `isolation` (Default `dir`), Gewichte.

## 4. Funktionale Anforderungen

- **FR-01:** **Pipeline-Budget.** `pipeline.budget.max_tokens` und `pipeline.budget.max_claude_tokens`
  in `config.yaml` sowie die Run-Optionen `--max-tokens` und `--max-claude-tokens` begrenzen die
  Tokens eines Runs. Die Optionen stehen in `run.json` und überschreiben die Config. Nach jedem
  Rollenaufruf summiert die Pipeline die Usage des Runs (`token_usage` mit seiner `run_id`).
  Claude-Tokens sind die der Rollen, die laut `run.json` mit `claude-cli` oder `anthropic` belegt
  sind. Bei Überschreitung hält der Run mit Grund `budget` (Exit 1); Session-Rollen zählen nicht.
- **FR-02:** **Suite-Art `e2e`.** Für jede Belegung und Wiederholung gilt:
  1. Arbeitsverzeichnis nach der Isolationsstrategie anlegen.
  2. Die Belegung als abgeleitete Profile und `llm.roles` in die `config.yaml` der Kopie schreiben;
     der Supervisor bleibt `inline`.
  3. Je Spec der Suite `sdd pipeline run SPEC --auto --steps ""` mit dem Budget der Matrix als
     Prozess starten. Ein Run mit Grund `budget` beendet den Lauf; andere Ausgänge gehen zur
     nächsten Spec.
  4. Messen (FR-03), dann aufräumen.
- **FR-03:** **Messung (Proxy).** Erst nach dem letzten Run werden `hidden/` ins Arbeitsverzeichnis
  kopiert und die Akzeptanztests ausgeführt (JUnit). Daraus ergeben sich:
  - `frs_total` und `frs_met` aus den FR-Markern der Testnamen; eine FR ist erfüllt, wenn alle ihre
    Tests grün sind. `Q_req = frs_met / frs_total`.
  - `Q_arch` und `Q_code` aus `sdd quality measure --diff <start>` im Arbeitsverzeichnis
    (Teilscores `architecture` und `code_quality`).
  - `Q` nach den Gewichten der Suite.
  - Tokens je Rolle aus der Usage der Runs im Arbeitsverzeichnis. Geschätzte oder fehlende Usage
    wird als `estimated` markiert.
- **FR-04:** **Isolation (Strategy).** `isolation: dir` ist die einzige Umsetzung. Eine unbekannte
  Isolationsart ergibt Exit 2 vor dem ersten Lauf. Das Projekt-Worktree und `.sdd/` des Projekts
  bleiben unverändert.
- **FR-05:** **Fixture `todo-service`** (Python-Standardbibliothek, Schichten
  `domain`/`service`/`persistence`/`cli` mit `architecture.yaml`):
  - Drei Specs: klein (3 FRs), mittel (6 FRs), groß (10 FRs mit Schichtregeln).
  - Je Spec versteckte Akzeptanztests und die Referenzlösung.
  - Die Specs sind `approved`, ihre Gate-Phase ist `execute-unlocked`.
  - `sdd bench init` kopiert Fixture und Suite `e2e.yaml`.
- **FR-06:** **Ausgänge im Report.** Records mit `halted: budget` oder `error` zählen mit dem
  erreichten Stand. Der Report nennt je Eintrag die Zahl der Läufe je Ausgang (LSP-Befund).
- **FR-07:** **Schema.** `bench-matrix.schema.json` (CON-0221) wird additiv erweitert: `kind: e2e`
  verlangt `fixture`, `specs` und `test_command`. Doku in README und CHANGELOG.

## 5. Nicht-funktionale Anforderungen

| Kategorie   | Anforderung |
|-------------|-------------|
| Isolation   | Versteckte Tests und Referenz erreichen keinen Rollenkontext; das Projekt bleibt unverändert. |
| Keyfreiheit | Claude nur über `claude-cli`. |
| Laufzeit    | Die kleine Spec läuft mit einem lokalen Modell (≥ 30 tok/s) unter 30 min. |

## 6. Akzeptanzkriterien (Gherkin)

```gherkin
Feature: Suite e2e

  Scenario: Ganze Spec auf dem Fixture
    Given die Suite e2e mit der kleinen Spec von todo-service
    When ich "sdd bench run --suite e2e --repetitions 1" ausführe
    Then enthält results.jsonl je Belegung einen Record mit Q_req, Q_arch, Q_code und Tokens je Rolle

  Scenario: Pipeline-Budget
    Given ein Run mit --max-tokens 100
    When die Rollen mehr als 100 Tokens verbrauchen
    Then hält der Run mit Grund budget und Exit 1
```

## 7. Edge Cases & Fehlerfälle

- Run hält vor S3 (z. B. Supervisor `halt`): Messung des erreichten Stands, Ausgang `completed`
  mit niedrigem Q.
- Akzeptanztests laufen ins Zeitlimit: nicht erfüllte FRs, Grund im Record.
- `sdd quality measure` scheitert (fehlende Sonde): `Q_arch`/`Q_code` sind `null` und `Q`
  renormalisiert.

## 8. Contracts (was wird garantiert)

| Contract-ID | Typ      | Was wird garantiert? |
|-------------|----------|----------------------|
| CON-0225    | behavior | Pipeline-Budget (Config, Optionen, Zählung, Halt) |
| CON-0226    | behavior | Suite e2e, Isolation, Messung, Fixture, Ausgänge im Report |

## 9. Tests (wie wird verifiziert)

| Test-ID  | Level      | Was prüft der Test? |
|----------|------------|---------------------|
| TST-0254 | acceptance | Pipeline-Budget mit Fake-LLM-Server |
| TST-0255 | acceptance | e2e mit Fake-LLM-Server auf einem Mini-Fixture; Fixture-Selbsttest (Referenz grün, Start rot) |

## 10. Offene Fragen

- [x] Fixture-Stack: Python-Standardbibliothek (2026-09-27).
- [x] Budget: allgemeines Pipeline-Feature (2026-09-27).
- [x] Isolation: nur Verzeichnis, als Strategy (2026-09-27).
- [x] Nächtlicher CI-Lauf: Nicht-Ziel (2026-09-27).

## 11. Änderungshistorie

| Datum      | Version | Autor         | Änderung |
|------------|---------|---------------|----------|
| 2026-09-27 | 0.1.0   | Boris, Claude | Aus SPEC-0056 0.1.0 abgespalten (Review) |
| 2026-09-27 | 0.2.0   | Boris, Claude | Review: Pipeline-Budget, Stdlib-Fixture, Isolation als Strategy, Patterns |
