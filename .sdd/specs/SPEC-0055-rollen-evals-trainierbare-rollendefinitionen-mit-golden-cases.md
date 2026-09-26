---
id: SPEC-0055
title: "Rollen-Evals: trainierbare Rollendefinitionen mit Golden Cases"
type: feature
status: implemented
owner: "Boris"
created: 2026-09-25
updated: 2026-09-26
version: 0.2.1
priority: high
tags: [llm, roles, evals, prompt-engineering, holdout]
depends_on: [SPEC-0053, SPEC-0054, SPEC-0061, SPEC-0062]
contracts:
- CON-0217
- CON-0218
- CON-0219
- CON-0220
tests:
- TST-0246
- TST-0247
- TST-0248
- TST-0249
fr_test_map:
  FR-01: [TST-0246, TST-0248]
  FR-02: [TST-0246]
  FR-03: [TST-0248]
  FR-04: [TST-0247, TST-0248]
  FR-05: [TST-0247, TST-0248]
  FR-06: [TST-0247, TST-0248]
  FR-07: [TST-0249]
  FR-08: [TST-0247, TST-0249]
  FR-09: [TST-0248]
  FR-10: [TST-0249]
  FR-11: [TST-0248]
  FR-12: [TST-0248]
---

# Rollen-Evals: trainierbare Rollendefinitionen mit Golden Cases

> **Status:** approved · **Owner:** Boris · **Version:** 0.2.1

## 1. Kontext & Motivation

SPEC-0053 macht jede Rolle zu einer Datei mit System-Prompt und Vertrag. Ob eine Änderung am Prompt
die Rolle besser oder schlechter macht, lässt sich heute nur am echten Projekt ausprobieren. Das ist
teuer, nicht reproduzierbar und vermischt Prompt- mit Modelleffekten.

„Trainieren“ heißt hier **kein Fine-Tuning von Gewichten**, sondern die iterative Verbesserung der
Rollendefinition (Prompt, Kontextauswahl, Parameter) gegen eine feste Testmenge. Die Arbeit läuft
dialogisch mit Claude Code: Eval ausführen, Fehlschläge analysieren, Änderung vorschlagen, erneut
messen. Übernommen wird eine Änderung nur, wenn sie nachweislich nicht verschlechtert.

Um Überanpassung an die sichtbaren Fälle zu verhindern, nutzt die Spec das Holdout-Prinzip von
sdd-framer: Ein Teil der Fälle liegt unter `.sdd/holdout/`, ist für den Tuning-Dialog unsichtbar und
entscheidet über die Übernahme.

Bestand (Review 2026-09-26):

| Baustein | Stand | In dieser Spec |
|----------|-------|----------------|
| Modellprofile `llm.profiles` | vorhanden (SPEC-0061, CON-0212) | `--model` nutzt sie; neuer Profil-Schlüssel `requests_per_minute` |
| Check-Registry `pipeline/runner.py` | 6 Checks `(output, ctx) -> Probleme`, ohne Parameter und Score | wird zu `pipeline/checks.py` mit Kontexten, Parametern und Score |
| Judge | `sdd quality --judge` nutzt Komponente `evaluator`, Rubrik in `.sdd/roles/judge.md` | wird Rolle `judge` in `llm.roles` |
| Holdout-Scanner | 9 Stellen lesen `.sdd/holdout/` rekursiv | ignorieren künftig `.sdd/holdout/roles/` |
| Run-Protokoll | `store`/`monitor` (Facade, ADR-0006) | Quelle für `capture` |

## 2. Zielsetzung

**Primärziel:** Jede Rolle hat eine versionierte Menge von Golden Cases mit prüfbaren Erwartungen.
`sdd role eval` misst eine Rollendefinition auf einem Modell reproduzierbar, und ein geführter
Tuning-Zyklus übernimmt Prompt-Änderungen nur bei nachgewiesener Verbesserung.

**Erfolgskriterien (messbar):**
- [ ] Für jede der fünf Pipeline-Rollen liegen mindestens 8 Golden Cases im Blueprint, davon
      mindestens 3 als Holdout; alle Checks aus FR-03 haben einen Positiv- und einen Negativfall.
- [ ] `sdd role eval decomposer --model <profil> --runs 3` liefert Score, Streuung und Tokens je Fall.
- [ ] Ein Tuning-Zyklus mit `/sdd-role-tune` erzeugt eine neue Rollenversion mit Eval-Beleg
      (`baseline.json` vorher/nachher, Eintrag im Rollen-CHANGELOG) im Commit.
- [ ] Aus einem echten Pipeline-Fehlschlag entsteht mit einem Befehl ein neuer Golden Case.
- [ ] `sdd quality --judge` und die Rubrik der Evals laufen über die Rolle `judge`.

**Nicht-Ziele (explizit):**
- Kein Fine-Tuning und kein LoRA-Training von Modellgewichten.
- Kein automatischer Prompt-Optimierer ohne Mensch (DSPy o. Ä.); jede Übernahme wird bestätigt.
- Kein Vergleich vieler Modelle über ganze Specs; das ist der Benchmark (SPEC-0056).
- Kein Mutationswerkzeug einer bestimmten Sprache: Mutanten liegen als Patches im Fall.

## 3. Architektur & Design Patterns

Angenommen (Review 2026-09-26): **Strategy** (Checks), **Template Method** (Eval-Ablauf),
**Proxy** (Holdout-Maskierung), **Memento** (`baseline.json`).

### Ablage
```
.sdd/roles/decomposer.md                    # Rollendatei (SPEC-0053), unverändert
.sdd/roles/decomposer/
├── baseline.json                           # Memento: übernommener Stand, Scores je Fall
├── CHANGELOG.md                            # Übernahmen mit Score vorher → nachher
└── cases/DEC-001-crud-mit-auth/            # sichtbarer Fall
    ├── case.yaml
    ├── input/                              # eingefrorener Snapshot: spec.md, contracts/, repo/ …
    ├── reference/  hidden/  mutants/       # je nach Rolle (Referenzlösung, versteckte Tests,
    └── expected/                           #  Mutanten-Patches, erwartete Befunde)
.sdd/holdout/roles/decomposer/DEC-006-…/    # Holdout-Fall, gleiche Struktur, nie im Tuning-Kontext
.sdd/role-evals/<ts>-<rolle>-<profil>.json  # Reports (lokal, gitignored)
```

`case.yaml`:
```yaml
id: DEC-001
role: decomposer
origin: blueprint            # blueprint | captured:<run_id> | manual
draft: false
test_command: "sh run_tests.sh"   # nur für ausführungsbasierte Checks; läuft im Arbeitsverzeichnis
expect:
  checks:
    - fr_coverage: { min: 1.0 }
    - acyclic: {}
    - task_count: { min: 4, max: 9 }
    - ordered_before: { first: "Datenmodell", then: "API-Endpunkt" }
  rubric:
    - { id: granularity, question: "Ist jeder Task in einer Sitzung umsetzbar und einzeln testbar?" }
weights: { checks: 0.8, rubric: 0.2 }
```
Ob ein Fall Holdout ist, ergibt sich allein aus seinem Ort (`.sdd/holdout/roles/`).

### Strategy: Check-Registry
Checks sind registrierte, benannte Funktionen mit Deklaration: `contexts` (`gate`, `eval`),
benötigte Fall-Bestandteile (`reference`, `hidden`, `mutants`, `expected`) und Parameterschema.
Ein Check liefert `CheckResult(passed, score 0–1, details)`. Pipeline-Gates nutzen nur Checks mit
Kontext `gate`, die ohne Fall auskommen (LSP-Befund des Reviews).

### Template Method: Eval-Ablauf
Fester Ablauf je Fall und Lauf: Arbeitsverzeichnis anlegen und `input/` kopieren → Nonce setzen →
Rolle ausführen (RoleRunner, SPEC-0053) → Ausgabe anwenden → Checks → Rubrik (Judge) → Usage
schreiben → Arbeitsverzeichnis entfernen. Rollenspezifische Hooks: `prepare` (z. B. Stub oder
Diff mit eingebautem Fehler einspielen), `build_input`, `apply_output`.

### Proxy: Holdout-Sicht
Ein Proxy vor Fall-Repository und Report gibt Holdout-Fälle ohne `--include-holdout` nur als
aggregierten Score heraus. CLI, JSON-Report, `compare` und Skill sehen nur den Proxy.

### Memento und Ratchet
`baseline.json` hält den übernommenen Stand (Rollenversion, Prompt-Hash, Profil, Scores je Fall).
Eine neue Rollenversion wird nur übernommen, wenn gleichzeitig gilt: Gesamtscore nicht schlechter,
Holdout-Score nicht schlechter, kein Fall fällt von `pass` auf `fail`, `output_schema` unverändert.

### Schichten
Eval-Kern in `tool/sdd_cli/pipeline/evals/` (Schicht `pipeline`, nutzt RoleRunner), Checks in
`tool/sdd_cli/pipeline/checks.py`, CLI `tool/sdd_cli/role_cli.py` (`entry`). `sdd quality --judge`
erreicht die Rolle `judge` über `pipeline.facade` (ARCH-05).

## 4. Funktionale Anforderungen

- **FR-01:** **Fälle.** Sichtbare Fälle liegen unter `.sdd/roles/<rolle>/cases/<ID>/`, Holdout-Fälle
  unter `.sdd/holdout/roles/<rolle>/<ID>/`, jeweils mit `case.yaml` nach
  `role-case.schema.json` und `input/`; je nach Rolle zusätzlich `reference/`, `hidden/`,
  `mutants/*.patch` und `expected/`. `sdd role case new <rolle> [--holdout] --title "…"` vergibt die
  ID mit Präfix je Rolle (`DEC-`, `TAU-`, `IMP-`, `REV-`, `SUP-`, `JDG-`), eindeutig über beide Orte.
- **FR-02:** **Blueprint-Fälle.** Der Blueprint liefert für jede der fünf Pipeline-Rollen mindestens
  8 Fälle, davon mindestens 3 Holdout (`blueprint/roles/<rolle>/cases/`,
  `blueprint/holdout/roles/<rolle>/`). Implementer- und Test-Author-Fälle stammen aus der Methode in
  BEFUND-modelle-2026-09-24 §3: echte sdd-framer-Module mit versteckten Referenztests.
  `sdd init` und `sdd upgrade` installieren fehlende Fälle wie Rollen und überschreiben keine
  vorhandenen. Holdout-Fälle schreibt ein isolierter Agent; ihr Inhalt gelangt nie in den
  Kontext der Session, die Rollen tunt.
- **FR-03:** **Check-Registry.** `pipeline/checks.py` ersetzt die Registry in `runner.py`. Jeder
  Check deklariert Kontexte, benötigte Fall-Bestandteile und Parameter; eine Rolle oder ein Fall
  mit unbekanntem oder unpassendem Check wird beim Laden abgelehnt (`sdd validate`). Checks je Rolle:

  | Rolle | Checks |
  |-------|--------|
  | decomposer | json_schema, fr_coverage, acyclic, deps_resolvable, test_file_per_code_task, task_count, ordered_before, max_complexity |
  | test_author | fr_marker_present, red_against_stub, green_against_reference, mutation_kill_rate |
  | implementer | paths_allowed, hidden_tests_pass, arch_violations, quality_score |
  | reviewer | seeded_bug_recall, clean_diff_precision |
  | supervisor | decision_matches, reason_mentions |

  Ausführungsbasierte Checks (`red_against_stub`, `green_against_reference`, `mutation_kill_rate`,
  `hidden_tests_pass`) führen `test_command` des Falls im Arbeitsverzeichnis mit Zeitlimit aus;
  `mutation_kill_rate` wendet jeden Patch aus `mutants/` einzeln an und zählt die vom Test getöteten
  Mutanten. `arch_violations` und `quality_score` nutzen `sdd arch check` bzw. SPEC-0054 auf dem
  Arbeitsverzeichnis, wenn der Fall eine Konfiguration mitbringt, sonst `n/a`.
- **FR-04:** **`sdd role eval <rolle>`** `[--model PROFIL] [--version DATEI] [--runs N] [--case ID]
  [--include-holdout] [--concurrency N] [--dry-run] [--json]` führt die Rolle auf allen bzw.
  ausgewählten Fällen aus (Ablauf nach Abschnitt 3). Je Fall: Score (0–1), pass/fail (Mehrheit der
  Läufe), Check-Ergebnisse, Rubrikwerte, Tokens (in/out/reasoning), Dauer. Aggregiert: Mittelwert,
  Standardabweichung, `pass@1`, `pass^k`. `--dry-run` nennt Aufrufzahl und geschätzte Tokens aus
  früheren Reports. Entwurfsfälle (`draft: true`) zählen nicht.
- **FR-05:** **Holdout-Sichtbarkeit.** Ohne `--include-holdout` erscheinen Holdout-Fälle in CLI,
  Report und `compare` nur als aggregierter Score und Anzahl, ohne ID, Eingaben, Ausgaben oder
  Details. Alle Scanner von `.sdd/holdout/` (Evaluator, `holdout run`, `holdout generate`, Web-API,
  Statuszählung) ignorieren `.sdd/holdout/roles/` über eine gemeinsame Funktion.
- **FR-06:** **Report.** Jeder Lauf wird nach `.sdd/role-evals/<ts>-<rolle>-<profil>.json`
  geschrieben (`role-eval-report.schema.json`): Rollenversion, Prompt-Hash, Profil, Judge-Modell und
  Rubrikversion, sdd-Version, Ergebnisse. Das Verzeichnis ist rechnerlokal (gitignored). Usage
  landet in `token_usage` mit Kontext `origin: role-eval`, Rolle, Fall und Lauf.
- **FR-07:** **`sdd role compare <report-a> <report-b>`** zeigt je sichtbarem Fall das Delta und
  wendet die Ratchet-Regel an: `accept` oder `reject` mit Begründung (regressierter Fall, gesunkener
  Score, geänderte `output_schema`). Exit 0 bei `accept`, 1 bei `reject`.
- **FR-08:** **`sdd role accept <rolle> --report <pfad>`** übernimmt eine Kandidatenversion, nur
  wenn `compare` gegen `baseline.json` `accept` ergibt (sonst Abbruch, außer mit
  `--force --reason "…"`, protokolliert). Getrennte Schritte: Version erhöhen (Minor bei
  Prompt-Änderung, Patch bei Parametern), Rollendatei schreiben, `baseline.json` ersetzen,
  CHANGELOG-Eintrag (Datum, Änderung, Score vorher → nachher). Ziel ist die geladene Rollendatei,
  wenn sie im Projekt liegt (im sdd-framer-Repo also der Blueprint), sonst `.sdd/roles/<rolle>.md`.
- **FR-09:** **`sdd role case capture <run_id> <task_id|request_id>`** erzeugt aus einem
  Pipeline-Run einen Entwurfsfall (`draft: true`, `origin: captured:<run_id>`). Eingaben und
  gescheiterte Checks liest er über `pipeline.store`/`monitor`; Task-IDs liefern Fälle der
  Arbeitsrollen, Request-IDs (S1–S3) Fälle des Supervisors. `sdd role case confirm <ID>` hebt den
  Entwurf auf.
- **FR-10:** **Skill `/sdd-role-tune <rolle> [--model PROFIL]`** (Repo und Blueprint):
  1. Baseline-Eval, Fehlschläge nach Ursache gruppieren (nur sichtbare Fälle).
  2. **Eine** gezielte Änderung an Prompt, Kontextquellen oder Parametern als Kandidatendatei, mit
     Hypothese.
  3. Kandidat evaluieren, `sdd role compare`.
  4. Bei `accept` Diff und Zahlen dem Nutzer vorlegen, dann `sdd role accept`; bei `reject` zurück
     zu 2, höchstens `n` Iterationen (Default 3).

  Der Skill verbietet, Fälle oder Checks zu ändern, um einen Score zu verbessern, `--include-holdout`
  zu nutzen und Pfade mit dem Segment `holdout` zu lesen.
- **FR-11:** **Profile.** `--model` verweist auf `llm.profiles.<name>`; ohne `--model` gilt die
  Belegung aus `llm.roles.<rolle>`. Neuer Profil-Schlüssel `requests_per_minute` begrenzt die Rate je
  Endpunkt (auch für SPEC-0056).
- **FR-12:** **Rolle `judge`.** `.sdd/roles/judge.md` wird eine Rollendatei (Frontmatter nach
  CON-0199, Rubrik im Text, Ausgabe `{"scores": {...}, "begruendung": "…"}`), belegt über
  `llm.roles.judge` (Default `claude-cli`). Sie bewertet die Rubrik-Items der Evals blind (ohne
  Modellnamen und Rollenversion) und ersetzt die Komponente `evaluator` in `sdd quality --judge`.
  Nutzt der Judge denselben Endpunkt wie das bewertete Profil, warnt `sdd role eval`.

## 5. Nicht-funktionale Anforderungen

| Kategorie      | Anforderung |
|----------------|-------------|
| Reproduzierbarkeit | Pro Aufruf ein Cache-Nonce; `seed`, wenn der Provider ihn kennt; Default `--runs 3`. |
| Isolation      | Fälle laufen in temporären Verzeichnissen; das Projekt bleibt unverändert (Prüfung wie der Repo-Guard in `tests/conftest.py`). |
| Sprachneutral  | Ausführung nur über `test_command` des Falls; Mutanten als Patches. |
| Kosten         | `--dry-run` vor dem Lauf; Zeitlimit je Befehl (Default 120 s). |
| Parallelität   | `--concurrency N` je Endpunkt, Default 2; `requests_per_minute` aus dem Profil. |

## 6. Akzeptanzkriterien (Gherkin)

```gherkin
Feature: Rollen-Evals

  Scenario: Eval eines Decomposers
    Given die Rolle decomposer hat 5 sichtbare und 3 Holdout-Fälle
    When ich "sdd role eval decomposer --model lokal --runs 3 --json" ausführe
    Then enthält der Report 5 Fälle mit Details und einen aggregierten Holdout-Score
    And jeder Fall hat input_tokens, output_tokens und reasoning_tokens

  Scenario: Ratchet verhindert Regression
    Given der Kandidat verbessert den Gesamtscore um 0,05
    And Fall DEC-003 fällt von pass auf fail
    When ich "sdd role compare base.json kandidat.json" ausführe
    Then ist das Ergebnis "reject" mit Verweis auf DEC-003

  Scenario: Fall aus echtem Fehlschlag
    Given Run r-42 enthält eine S1-Entscheidung "revise" wegen fehlender FR-Abdeckung
    When ich "sdd role case capture r-42 req-3" ausführe
    Then existiert ein neuer Fall SUP-xxx mit draft: true und Check decision_matches
```

## 7. Edge Cases & Fehlerfälle

- Nicht deterministische Modelle: `pass` bei Mehrheit der Läufe; `pass^k` zeigt die Stabilität.
- Veraltete Referenzlösung: Fälle tragen eingefrorene Snapshots und hängen nicht vom Repo-Stand ab.
- Kandidat ändert `output_schema`: `compare` lehnt ab (Contract-Änderung nach SPEC-0053 nötig).
- Weniger als 3 Holdout-Fälle: `sdd role eval` warnt, die Ratchet-Regel ist eingeschränkt.
- `test_command` läuft in das Zeitlimit: Check `failed` mit Grund, der Lauf geht weiter.
- Check braucht `reference/`, der Fall hat keine: `sdd validate` meldet den Fall.

## 8. Contracts (was wird garantiert)

| Contract-ID | Typ      | Was wird garantiert? |
|-------------|----------|----------------------|
| CON-0217    | data     | `role-case.schema.json` (`case.yaml`) |
| CON-0218    | data     | `role-eval-report.schema.json` und `baseline.json` |
| CON-0219    | behavior | Check-Registry, Eval-Ablauf, Holdout-Sichtbarkeit, `capture`, Rolle `judge` |
| CON-0220    | behavior | Ratchet (`compare`/`accept`), Versionierung, Skill `/sdd-role-tune` |

## 9. Tests (wie wird verifiziert)

| Test-ID  | Level       | Was prüft der Test? |
|----------|-------------|---------------------|
| TST-0246, TST-0247 | unit | Schemas, Score-Formel, Aggregation; jeder Check mit Positiv- und Negativfall; Aggregation; Ratchet |
| TST-0248, TST-0249 | acceptance | Szenarien der Contracts CON-0219 und CON-0220 mit Fake-LLM-Server auf Fixture-Fällen |
| TST-0246 | unit | Blueprint-Fälle: Anzahl, Schema, jeder Check-Fall läuft mit der Referenz grün |

## 10. Offene Fragen

- [x] Golden Cases im Blueprint ausliefern: ja, `init`/`upgrade` installieren sie (2026-09-26).
- [x] Default-Judge → `claude-cli` über Rolle `judge` (2026-09-25, Rolle 2026-09-26).
- [x] Holdout-Fälle unter `.sdd/holdout/roles/` (2026-09-26).
- [x] Umfang: alle fünf Rollen einschließlich ausführungsbasierter Checks in dieser Spec (2026-09-26).

## 11. Änderungshistorie

| Datum      | Version | Autor         | Änderung |
|------------|---------|---------------|----------|
| 2026-09-25 | 0.1.0   | Boris, Claude | Initiale Erstellung |
| 2026-09-26 | 0.2.0   | Boris, Claude | Review: Check-Kontexte (LSP), Holdout unter `.sdd/holdout/roles/`, Rolle `judge`, `capture` über Facade, Patterns |
| 2026-09-26 | 0.2.1   | Boris, Claude | Umsetzung: `max_complexity` statt `max_context_size` (die Decomposer-Ausgabe hat keine Kontextgröße) |
