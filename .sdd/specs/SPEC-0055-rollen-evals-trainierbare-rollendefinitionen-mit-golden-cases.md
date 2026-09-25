---
id: SPEC-0055
title: "Rollen-Evals: trainierbare Rollendefinitionen mit Golden Cases"
type: feature
status: draft
owner: "Boris"
created: 2026-09-25
updated: 2026-09-25
version: 0.1.0
priority: high
tags: [llm, roles, evals, prompt-engineering, holdout]
depends_on: [SPEC-0053, SPEC-0054]
contracts: []
tests: []
---

# Rollen-Evals: trainierbare Rollendefinitionen mit Golden Cases

> **Status:** draft · **Owner:** Boris · **Version:** 0.1.0

## 1. Kontext & Motivation

SPEC-0053 macht jede Rolle zu einer Datei mit System-Prompt und Vertrag. Ob eine Änderung am Prompt
die Rolle besser oder schlechter macht, lässt sich heute nur am echten Projekt ausprobieren. Das ist
teuer, nicht reproduzierbar und vermischt Prompt- mit Modelleffekten.

„Trainieren“ heißt hier **kein Fine-Tuning von Gewichten**, sondern die iterative Verbesserung der
Rollendefinition (Prompt, Kontextauswahl, Parameter) gegen eine feste Testmenge. Die Arbeit läuft
dialogisch mit Claude Code: Eval ausführen, Fehlschläge analysieren, Änderung vorschlagen, erneut
messen. Übernommen wird eine Änderung nur, wenn sie nachweislich nicht verschlechtert.

Um Überanpassung an die sichtbaren Fälle zu verhindern, nutzt die Spec das bewährte Holdout-Prinzip
von sdd-framer: Ein Teil der Fälle ist für den Tuning-Dialog unsichtbar und entscheidet über die
Übernahme.

## 2. Zielsetzung

**Primärziel:** Jede Rolle hat eine versionierte Menge von Golden Cases mit prüfbaren Erwartungen.
`sdd role eval` misst eine Rollendefinition auf einem Modell reproduzierbar, und ein geführter
Tuning-Zyklus übernimmt Prompt-Änderungen nur bei nachgewiesener Verbesserung.

**Erfolgskriterien (messbar):**
- [ ] Für jede der fünf Rollen liegen mindestens 8 Golden Cases im Blueprint, davon mindestens 3
      als Holdout.
- [ ] `sdd role eval decomposer --model <m> --runs 3` liefert Score, Streuung und Tokens je Fall.
- [ ] Ein Tuning-Zyklus mit `/sdd-role-tune` erzeugt eine neue Rollenversion mit Eval-Beleg
      (`baseline.json` vorher/nachher) im Commit.
- [ ] Aus einem echten Pipeline-Fehlschlag (SPEC-0053) entsteht mit einem Befehl ein neuer
      Golden Case.

**Nicht-Ziele (explizit):**
- Kein Fine-Tuning und kein LoRA-Training von Modellgewichten.
- Kein automatischer Prompt-Optimierer ohne Mensch (DSPy o. Ä.); jede Übernahme wird bestätigt.
- Kein Vergleich vieler Modelle über ganze Specs; das ist der Benchmark (SPEC-0056).

## 3. Architektur & Design Patterns

### Golden Case als Daten
```
.sdd/roles/decomposer/
├── baseline.json                 # letzter übernommener Stand: Rollenversion, Modell, Scores je Fall
└── cases/
    ├── DEC-001-crud-mit-auth/
    │   ├── case.yaml             # Beschreibung, Holdout-Flag, Herkunft, erwartete Checks
    │   └── input/                # spec.md, contracts/, agents_md.md, repo_map.txt …
    └── DEC-007-zyklus-falle/ …
```

`case.yaml`:
```yaml
id: DEC-001
role: decomposer
holdout: false
origin: blueprint            # blueprint | captured:<run_id> | manual
expect:
  checks:                    # deterministisch, aus der Check-Registry
    - fr_coverage: { min: 1.0 }
    - acyclic: {}
    - task_count: { min: 4, max: 9 }
    - ordered_before: { first: "Datenmodell", then: "API-Endpunkt" }   # Titel-Muster
    - max_context_size: { value: M }
  rubric:                    # optional, LLM-Judge, 1–5
    - { id: granularity, question: "Ist jeder Task in einer Sitzung umsetzbar und einzeln testbar?" }
weights: { checks: 0.8, rubric: 0.2 }
```

### Registry + Strategy: Checks
Checks sind registrierte, benannte Funktionen `check(output, case, workspace) -> CheckResult`. Sie
werden in SPEC-0053 (Rollen-Gates) und hier (Evals) gemeinsam genutzt. Rollenspezifische Checks:

| Rolle        | Checks (Auswahl)                                                              |
|--------------|-------------------------------------------------------------------------------|
| decomposer   | json_schema, fr_coverage, acyclic, deps_resolvable, task_count, ordered_before, test_file_per_code_task |
| test_author  | red_against_stub, green_against_reference, mutation_kill_rate (gegen Referenzlösung), fr_marker_present |
| implementer  | hidden_tests_pass, quality_score (SPEC-0054), arch_violations == 0, paths_allowed |
| reviewer     | seeded_bug_recall (Diffs mit eingebautem Fehler), clean_diff_precision (keine Fehlalarme) |
| supervisor   | decision_matches (erwartete Entscheidung), reason_mentions (Beleg genannt)    |

### Ratchet: Übernahmeregel
Eine neue Rollenversion wird nur übernommen, wenn gleichzeitig gilt: der Gesamtscore über alle
Fälle ist nicht schlechter, der Holdout-Score ist nicht schlechter, und kein Fall fällt von `pass`
auf `fail`. So kann jede Iteration nur halten oder verbessern.

## 4. Funktionale Anforderungen

- **FR-01:** Golden Cases liegen unter `.sdd/roles/<rolle>/cases/<ID>/` mit `case.yaml` nach
  `contracts/data/role-case.schema.json` und einem Verzeichnis `input/`. IDs haben je Rolle ein
  Präfix (`DEC-`, `TAU-`, `IMP-`, `REV-`, `SUP-`) und werden von `sdd role case new` vergeben.
- **FR-02:** Der Blueprint liefert für jede Rolle mindestens 8 Fälle, davon mindestens 3 mit
  `holdout: true`. Ein Teil der Implementer- und Test-Author-Fälle stammt aus der Methode in
  BEFUND-modelle-2026-09-24 §3: echte sdd-framer-Module mit versteckten Referenztests.
- **FR-03:** `sdd role eval <rolle> [--model PROFIL] [--version DATEI] [--runs N] [--case ID]
  [--include-holdout] [--json]` führt die Rolle auf allen bzw. ausgewählten Fällen aus. Jeder Fall
  läuft in einem temporären Arbeitsverzeichnis. Ausgegeben werden je Fall: Score (0–1),
  pass/fail, Check-Ergebnisse, Rubrikwerte, Tokens (in/out/reasoning), Dauer. Aggregiert:
  Mittelwert, Standardabweichung, `pass@1` und `pass^k` (alle k Läufe bestanden).
- **FR-04:** Ohne `--include-holdout` erscheinen Holdout-Fälle in der Ausgabe nur als aggregierter
  Score, ohne Eingaben, Ausgaben oder Check-Details. Die Tuning-Session bekommt ihren Inhalt nie zu
  sehen (analog `.sdd/holdout/`).
- **FR-05:** Jeder Eval-Lauf wird nach `.sdd/role-evals/<ts>-<rolle>-<modell>.json` persistiert
  (Schema `role-eval-report.schema.json`), inklusive Rollenversion, Prompt-Hash, Modellprofil und
  sdd-Version. Die Usage landet zusätzlich in `token_usage` mit `component = role-eval`.
- **FR-06:** `sdd role compare <report-a> <report-b>` zeigt je Fall das Delta und wendet die
  Ratchet-Regel an: Ergebnis `accept` oder `reject` mit Begründung (welcher Fall regressiert ist,
  welcher Score gesunken ist).
- **FR-07:** `sdd role accept <rolle> --report <pfad>` übernimmt eine Kandidatenversion. Der Befehl
  erhöht die `version` in der Rollendatei (Minor bei Prompt-Änderung, Patch bei Parametern),
  aktualisiert `baseline.json` und hängt einen Eintrag an `.sdd/roles/<rolle>/CHANGELOG.md` an:
  Datum, Änderung, Score vorher → nachher. Ohne `accept` aus `compare` bricht er ab, außer mit
  `--force --reason "…"`, und auch dann wird das protokolliert.
- **FR-08:** `sdd role case capture <run_id> <task_id|decision_id>` erzeugt aus einem
  Pipeline-Run (SPEC-0053) einen neuen Fall. Er übernimmt die tatsächlichen Eingaben als `input/`
  und legt ein `case.yaml` mit den Checks an, die gescheitert sind. `expect` wird zur Bearbeitung
  geöffnet; der Fall ist bis zur Bestätigung `draft: true` und zählt nicht in Scores.
- **FR-09:** Neuer Skill `/sdd-role-tune <rolle> [--model PROFIL]` beschreibt den Tuning-Zyklus für
  Claude Code:
  1. Baseline-Eval ausführen, Fehlschläge nach Ursache gruppieren (nur sichtbare Fälle).
  2. **Eine** gezielte Änderung an Prompt, Kontextquellen oder Parametern als Kandidatendatei
     vorschlagen, mit Hypothese.
  3. Kandidat evaluieren, `sdd role compare` ausführen.
  4. Bei `accept` die Änderung dem Nutzer mit Diff und Zahlen zur Bestätigung vorlegen, dann
     `sdd role accept`. Bei `reject` zurück zu Schritt 2, maximal `n` Iterationen (Default 3).

  Der Skill verbietet, Fälle oder Checks zu ändern, um einen Score zu verbessern. Neue Fälle kommen
  nur über `capture` oder ausdrücklich vom Nutzer.
- **FR-10:** Modellprofile (`--model`) verweisen auf Einträge in `llm.profiles.<name>` in
  `config.yaml` (Provider, Modell, Endpunkt, Parameter). Dieselben Profile nutzt SPEC-0056.
  Ohne `--model` wird die in `llm.roles.<rolle>` konfigurierte Belegung verwendet.
- **FR-11:** Rubrik-Items werden von der Rolle `judge` (SPEC-0054 FR-09) bewertet. Der Judge sieht
  weder Modellnamen noch Rollenversion (Blind-Bewertung). Judge-Modell und Rubrikversion stehen im
  Report.

## 5. Nicht-funktionale Anforderungen

| Kategorie      | Anforderung                                                                 |
|----------------|-----------------------------------------------------------------------------|
| Reproduzierbarkeit | Pro Aufruf ein Cache-Nonce; `seed` wird gesetzt, wenn der Provider ihn unterstützt; Default `--runs 3`. |
| Isolation      | Fälle laufen in temporären Verzeichnissen; das Projekt-Worktree bleibt unverändert (bestehender Repo-Guard aus `tests/conftest.py` als Vorbild). |
| Kosten         | `--dry-run` zeigt vor dem Lauf die Zahl der Aufrufe und die geschätzten Tokens aus früheren Reports. |
| Parallelität   | `--concurrency N` je Endpunkt, Default 2; Rate-Limits (z. B. 60 req/min) sind über das Profil konfigurierbar. |

## 6. Akzeptanzkriterien (Gherkin)

```gherkin
Feature: Rollen-Evals

  Scenario: Eval eines Decomposers
    Given die Rolle decomposer hat 8 Fälle, davon 3 holdout
    When ich "sdd role eval decomposer --model qwen-think --runs 3 --json" ausführe
    Then enthält der Report 5 Fälle mit Details und einen aggregierten Holdout-Score
    And jeder Fall hat input_tokens, output_tokens und reasoning_tokens

  Scenario: Ratchet verhindert Regression
    Given der Kandidat verbessert den Gesamtscore um 0,05
    And Fall DEC-003 fällt von pass auf fail
    When ich "sdd role compare base.json kandidat.json" ausführe
    Then ist das Ergebnis "reject" mit Verweis auf DEC-003

  Scenario: Fall aus echtem Fehlschlag
    Given Run r-42 enthält eine S1-Entscheidung "revise" wegen fehlender FR-Abdeckung
    When ich "sdd role case capture r-42 d-3" ausführe
    Then existiert ein neuer Fall DEC-xxx mit draft: true und Check fr_coverage
```

## 7. Edge Cases & Fehlerfälle

- Nicht deterministische Modelle: Ein Fall gilt als `pass`, wenn die Mehrheit der Läufe besteht;
  `pass^k` zeigt die Stabilität getrennt.
- Referenzlösung eines Implementer-Falls veraltet durch Änderungen am Projekt: Fälle tragen einen
  eingefrorenen `input/`-Snapshot und hängen nicht vom aktuellen Repo-Stand ab.
- Kandidat ändert `output_schema` der Rolle: `compare` lehnt ab, weil Schemaänderungen eine
  Contract-Änderung nach SPEC-0053 erfordern.
- Holdout-Anteil unter 3 Fälle: `sdd role eval` warnt, dass die Ratchet-Regel nur eingeschränkt
  aussagekräftig ist.

## 8. Contracts (was wird garantiert)

| Contract-ID | Typ      | Was wird garantiert?                                         |
|-------------|----------|--------------------------------------------------------------|
| CON-XXXX    | data     | `role-case.schema.json`                                      |
| CON-XXXX    | data     | `role-eval-report.schema.json`                               |
| CON-XXXX    | behavior | Ratchet-Regel (`compare`/`accept`) als Gherkin               |
| CON-XXXX    | behavior | Holdout-Sichtbarkeit in Ausgaben und Skill                   |
| CON-XXXX    | data     | `llm.profiles`-Block in `config.yaml`                        |

## 9. Tests (wie wird verifiziert)

| Test-ID  | Level       | Was prüft der Test?                                               |
|----------|-------------|-------------------------------------------------------------------|
| TST-XXXX | unit        | Jeder Check der Registry mit Positiv- und Negativfall             |
| TST-XXXX | unit        | Aggregation (Mittel, Std, pass@1, pass^k), Ratchet-Entscheidung   |
| TST-XXXX | integration | `sdd role eval` mit FakeProvider auf Fixture-Fällen, Holdout-Maskierung |
| TST-XXXX | acceptance  | Gherkin-Szenarien aus Abschnitt 6                                 |

## 10. Offene Fragen

- [ ] Sollen die Golden Cases im Blueprint an jedes neue Projekt ausgeliefert werden, oder nur in
      sdd-framer liegen und projektspezifische Fälle über `capture` entstehen? Vorschlag: Blueprint
      liefert sie, weil ohne Startmenge kein Tuning möglich ist.
- [x] Default-Judge → `claude-cli` (entschieden 2026-09-25).

## 11. Änderungshistorie

| Datum      | Version | Autor         | Änderung            |
|------------|---------|---------------|---------------------|
| 2026-09-25 | 0.1.0   | Boris, Claude | Initiale Erstellung |
