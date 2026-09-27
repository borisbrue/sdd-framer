---
id: SPEC-0056
title: "Benchmark-Strecke: Modellvergleich nach Tokens und Qualität"
type: feature
status: draft
owner: "Boris"
created: 2026-09-25
updated: 2026-09-27
version: 0.2.0
priority: high
tags: [benchmark, llm, local-llm, metrics, token-tracking, quality]
depends_on: [SPEC-0053, SPEC-0054, SPEC-0055, SPEC-0061]
contracts: []
tests: []
---

# Benchmark-Strecke: Modellvergleich nach Tokens und Qualität

> **Status:** draft · **Owner:** Boris · **Version:** 0.2.0

## 1. Kontext & Motivation

Die Modellwahl erfolgt heute aus einmaligen, handgeschriebenen Untersuchungen
(BEFUND-modelle-2026-09-24). Die Skripte dazu liegen nicht im Repo, die Ergebnisse sind nicht
wiederholbar. Welche Modellbelegung **pro verbrauchtem Token** die beste Qualität liefert, lässt sich
nicht beantworten.

Diese Spec macht daraus eine wiederholbare Strecke im Repo. Sie nutzt die Rollen-Evals (SPEC-0055)
als schnelle Vorstufe und die Qualitätsmessung (SPEC-0054) als Messgerät. Die teuerste Stufe, ganze
Pipeline-Runs auf einem Fixture-Projekt, ist nach SPEC-0063 abgespalten (Review 2026-09-27).

Bestand:

| Baustein | Stand | Nutzung hier |
|----------|-------|--------------|
| Profile `llm.profiles`, `requests_per_minute` | vorhanden (SPEC-0061, SPEC-0055) | Belegungen der Matrix; neue Profil-Schlüssel `max_concurrent`, `seed` |
| Rollen-Evals `pipeline.evals` | vorhanden (SPEC-0055) | Suite `roles` |
| Qualitätsmessung `quality.measure` | vorhanden (SPEC-0054) | Messung der Suite `regen` |
| Usage mit `server_model`, `source` | vorhanden (SPEC-0060) | Tokens, Modellnamen, Schätzungen |
| Module aus BEFUND §3 | 7 von 8 vorhanden (`dag_event` seit SPEC-0058 entfernt) | Suite `regen` für sdd-framer |

## 2. Zielsetzung

**Primärziel:** `sdd bench run` vergleicht beliebige Modellbelegungen über eine feste Aufgabenmenge
und zeigt je Belegung Qualität gegen Tokenverbrauch (Input, Output, Reasoning) mit Pareto-Front.

**Erfolgskriterien (messbar):**
- [ ] Die Methode von BEFUND-modelle §3 ist als Suite `regen` reproduzierbar: Zwei Läufe mit gleicher
      Konfiguration unterscheiden sich im Mittel um höchstens die gemessene Streuung.
- [ ] Ein Report beantwortet je Rolle: welches Profil hat die höchste Qualität, welches das beste
      Verhältnis Qualität/Token, und welche Profile liegen auf der Pareto-Front.
- [ ] Jede Kennzahl im Report ist bis zum einzelnen Lauf zurückverfolgbar.
- [ ] `sdd bench run|report|compare` verändern weder das Projekt-Worktree noch `.sdd/` des Projekts.

**Nicht-Ziele (explizit):**
- Kein öffentliches Leaderboard, kein Upload von Ergebnissen.
- Kein Hosting oder Laden von Modellen; die Endpunkte müssen laufen.
- Keine reinen Durchsatzmessungen (TTFT, tok/s); dafür bleibt `sdd config test-llm` zuständig.
- Keine ganzen Pipeline-Runs und kein Fixture-Projekt (SPEC-0063).

## 3. Architektur & Design Patterns

Angenommen (Review 2026-09-27): **Template Method** (BenchTask), **Decorator** (Provider-Hüllen),
**Proxy** (versteckte Tests), **Memento** (`results.jsonl` als Fortschritt und Vergleichsstand).

### Ablage im Projekt
```
bench/
├── matrix.yaml               # Profile, Belegungen, Varianten, Sweep, Wiederholungen, Budget
├── suites/<name>.yaml        # Suite: kind (roles | regen | …), Aufgaben, Gewichte
└── results/<ts>/             # results.jsonl, report.md, report.html, runs/<lauf-id>/ (gitignored)
```
`sdd bench init` legt `bench/` aus den Vorlagen des Blueprints an (Matrix-Beispiel, Suite `roles`);
im sdd-framer-Repo liegt zusätzlich `bench/suites/regen.yaml` mit den Modulen aus BEFUND §3.

`matrix.yaml`:
```yaml
suites: [roles, regen]
repetitions: 3
top_k: 2                                # Stufenmodell: beste Profile je Rolle aus roles → regen
assignments:
  - name: all-qwen38
    roles: {decomposer: "qwen38-27b@think", "*": qwen35-a3b, supervisor: claude}
variants:
  think: {thinking: true}
  high: {reasoning_effort: high}
sweep: {role: implementer, profiles: [qwen35-a3b, qwen38-27b, gpt-oss-120b]}
budget: {max_tokens: 2000000, max_claude_tokens: 200000}
```

### Template Method: BenchTask und Suite-Registry
Jede Suite-Art ist ein `BenchTask` mit festem Ablauf `prepare(workspace)` → `run(assignment)` →
`measure()` → `teardown()` und wird über `kind` in einer Registry gefunden (OCP-Befund). `measure()`
ist je Art festgelegt und liefert einen `q_kind`: `roles` → `eval` (Score nach SPEC-0055),
`regen` → `quality` (Tests plus SPEC-0054). Report, Pareto-Front, Signifikanz und `compare`
vergleichen nur Records mit gleichem `q_kind` (LSP-Befund).

### Decorator: Provider-Hüllen
Um jeden Provider eines Laufs legen sich Hüllen für Zählung (Tokens je Rolle, Aufrufe), Budget
(`BudgetExceeded` → Ausgang `halted: budget`), Rate-Limit und Parallelität je Endpunkt
(`requests_per_minute`, `max_concurrent`) und Schätzung fehlender Usage (`estimated: true`).
`seed` setzt der Provider selbst, wenn er ihn kennt (`openai-compat`).

### Proxy: versteckte Tests und Referenz
Versteckte Tests und Referenzlösung liegen außerhalb des Arbeitsverzeichnisses und werden erst in
`measure()` eingespielt, nach dem letzten Rollenaufruf.

### Schichten
Paket `tool/sdd_cli/bench/` (Schicht `cli`), CLI `tool/sdd_cli/bench_cli.py` (`entry`).
Rollenaufrufe nur über `pipeline.facade` (neue Funktion `run_role`) bzw. `pipeline.evals`
(ARCH-05), keine Subprozesse.

## 4. Funktionale Anforderungen

- **FR-01:** **`sdd bench run`** `--matrix bench/matrix.yaml [--suite NAME] [--only ASSIGNMENT]
  [--repetitions N] [--concurrency N] [--dry-run] [--resume ORDNER]` expandiert die Matrix
  (Varianten `profil@variante`, `*`-Belegung, Sweep) und führt je Suite, Belegung und Wiederholung
  einen Lauf aus; Ergebnisse nach `bench/results/<ts>/`. `--dry-run` zeigt Zahl der Läufe und
  geschätzte Tokens aus früheren Ergebnissen.
- **FR-02:** **Isolation.** Jeder Lauf arbeitet in einem frischen temporären Verzeichnis (Kopie bzw.
  `git worktree` am festen Commit der Suite). Versteckte Tests und Referenz werden erst zur Messung
  eingespielt; kein Rollenkontext enthält sie. Projekt-Worktree und `.sdd/` bleiben unverändert.
- **FR-03:** **Suite `roles`** (`kind: roles`) führt für jede Rolle × jedes Profil der Matrix die
  Rollen-Evals aus SPEC-0055 aus (sichtbare und Holdout-Fälle, Holdout nur aggregiert) und schreibt
  je Rolle und Profil einen Record mit `q_kind: eval`.
- **FR-04:** **Suite `regen`** (`kind: regen`) nennt ein Projekt (Pfad, Default das eigene), einen
  festen Commit, eine Liste `{module, tests}` und einen `test_command`. Je Modul: Modul im
  Arbeitsverzeichnis entfernen, die Rolle `implementer` erzeugt es aus Task (Pfad, Zweck aus dem
  Modul-Docstring) und den Unit-Tests neu (bis zu `attempts` Versuche mit Testausgabe als
  Rückmeldung), Messung mit den Tests und SPEC-0054 auf den erzeugten Dateien (`q_kind: quality`).
- **FR-05:** **Stufenmodell.** Mit `top_k` gehen je Rolle nur die besten Profile aus `roles` in die
  folgenden Suiten; der Report weist die Filterung aus.
- **FR-06:** **Record.** Jeder Lauf schreibt einen Record nach `results.jsonl`
  (`bench-record.schema.json`): Suite, Art, `q_kind`, Belegung, Profilparameter, Rollenversionen,
  Wiederholung, Ausgang (`completed`, `halted: budget`, `error`), `Q` und Teilscores, Tokens je Rolle
  (`T_in`, `T_out`, `T_reason`, `T_claude`, `estimated`), Aufrufe, Fehlversuche, Wandzeit,
  Endpunkt, gemeldeter Modellname, Git-SHA, sdd-Version, Verweis auf die Laufartefakte. Pflichtfelder
  hängen vom `q_kind` ab (ISP-Befund).
- **FR-07:** **`sdd bench report <ordner> [--html] [--by role|assignment] [--exclude-reasoning]`**
  erzeugt je `q_kind`: Tabelle je Belegung (Q, Teilscores als Mittel ± Std, Tokens, Tokens je
  erfülltem FR, Fehlversuche), Rangliste je Rolle nach Q und nach Effizienz `Q / (T / 1e5)`,
  Pareto-Front über (Q ↑, T ↓) getrennt „mit Claude-Tokens“ und „nur lokale Tokens“,
  Signifikanzhinweis (Unterschiede kleiner als die gepoolte Standardabweichung: „nicht
  unterscheidbar“). Geschätzte Tokens tragen ein Sternchen.
- **FR-08:** **`sdd bench compare <a> <b>`** vergleicht zwei Ergebnisordner je Belegung und
  `q_kind` mit Delta und Signifikanzhinweis und warnt, wenn der gemeldete Modellname eines Profils
  abweicht.
- **FR-09:** **Reproduzierbarkeit und Kosten.** Cache-Nonce je Aufruf (RoleRunner), `seed` aus dem
  Profil, Rate-Limit und `max_concurrent` je Endpunkt, `--resume` setzt fehlende Läufe fort (ein
  `error`-Lauf wird wiederholt, zählt aber nicht doppelt), Budget `max_tokens`/`max_claude_tokens`
  je Lauf.
- **FR-10:** **Vorlagen.** Der Blueprint liefert `bench/matrix.yaml` (Beispiel ohne Profile) und
  `bench/suites/roles.yaml`; `sdd bench init` legt sie an, ohne Vorhandenes zu überschreiben.
  `bench/results/` steht in den lokalen Ignores. Das sdd-framer-Repo erhält `bench/suites/regen.yaml`
  mit den sieben Modulen aus BEFUND §3.
- **FR-11:** **`sdd config apply-roles --from <ordner> --assignment NAME [--yes]`** (Konfiguration,
  nicht `sdd bench`) zeigt den `llm.roles`-Block der Belegung als Diff gegen `config.yaml` und
  schreibt ihn nur mit `--yes` bzw. nach Bestätigung (SRP-Befund).

## 5. Nicht-funktionale Anforderungen

| Kategorie         | Anforderung |
|-------------------|-------------|
| Isolation         | `run`, `report` und `compare` schreiben nur nach `bench/results/`. |
| Geheimnisse       | API-Keys stehen nur in Env-Variablen oder der Config, nie in Records oder Reports. |
| Keyfreiheit       | Claude nur über `claude-cli`; kein `ANTHROPIC_API_KEY` nötig. |
| Laufzeit          | Suite `roles` für 5 Rollen × 4 Profile × 3 Wiederholungen unter 60 min gegen einen lokalen Endpunkt mit ≥ 30 tok/s. |

## 6. Akzeptanzkriterien (Gherkin)

```gherkin
Feature: Benchmark-Strecke

  Scenario: Modellvergleich für die Rolle implementer
    Given matrix.yaml enthält einen sweep über drei Profile für die Rolle implementer
    When ich "sdd bench run --matrix bench/matrix.yaml --suite regen" ausführe
    And danach "sdd bench report bench/results/<ts> --by role"
    Then zeigt der Report für implementer drei Profile mit Q, T_in, T_out, T_reason
    And markiert die Profile auf der Pareto-Front

  Scenario: Versteckte Tests bleiben verborgen
    Given die Suite regen
    When ein Lauf die Rolle implementer aufruft
    Then enthält kein Rollenkontext die Referenzlösung des entfernten Moduls

  Scenario: Budget
    Given budget.max_claude_tokens ist 50000
    When ein Lauf 50000 Claude-Tokens überschreitet
    Then endet der Lauf mit halted: budget und der Record enthält den gemessenen Stand
```

## 7. Edge Cases & Fehlerfälle

- Endpunkt fällt mitten im Lauf aus: Ausgang `error`, `--resume` wiederholt ihn, ohne doppelt zu zählen.
- Modell auf dem Server ausgetauscht: gemeldeter Modellname im Record, `compare` warnt.
- Thinking-Modelle: `T_reason` getrennt; `--exclude-reasoning` klammert ihn in der Effizienz aus.
- Provider ohne Usage: Tokens geschätzt (`estimated: true`), im Report mit Sternchen.
- Unterschiedliche `q_kind` in einem Ordner: getrennte Abschnitte, nie ein gemeinsames Ranking.

## 8. Contracts (was wird garantiert)

| Contract-ID | Typ      | Was wird garantiert? |
|-------------|----------|----------------------|
| CON-XXXX    | data     | `bench-matrix.schema.json` und `bench-suite.schema.json` |
| CON-XXXX    | data     | `bench-record.schema.json` |
| CON-XXXX    | behavior | Lauf, Isolation, Suiten `roles`/`regen`, Budget, Resume |
| CON-XXXX    | behavior | Kennzahlen, Pareto, Signifikanz, `report`, `compare`, `config apply-roles` |

## 9. Tests (wie wird verifiziert)

| Test-ID  | Level       | Was prüft der Test? |
|----------|-------------|---------------------|
| TST-XXXX | unit        | Matrix-Expansion, Schemas |
| TST-XXXX | unit        | Kennzahlen, Pareto, Signifikanz aus Fixture-Records |
| TST-XXXX | acceptance  | `sdd bench run` mit Fake-LLM-Server (Suiten, Isolation, Budget, Resume) |
| TST-XXXX | acceptance  | `report`, `compare`, `config apply-roles` |

## 10. Offene Fragen

- [x] Umfang: Engine mit `roles` und `regen`; `e2e` und Fixture in SPEC-0063 (2026-09-27).
- [x] Übernahme in die Config: `sdd config apply-roles` (2026-09-27).
- [x] Vergleichbarkeit: `q_kind` trennt Eval- und Qualitätsscores (2026-09-27).
- [ ] Wo laufen die Benchmarks dauerhaft (lokal gegen den MLX-Server, mittwald über LiteLLM)?
      Beides über Profile möglich; Default-Profile im Blueprint bleiben leer.

## 11. Änderungshistorie

| Datum      | Version | Autor         | Änderung |
|------------|---------|---------------|----------|
| 2026-09-25 | 0.1.0   | Boris, Claude | Initiale Erstellung |
| 2026-09-27 | 0.2.0   | Boris, Claude | Review: e2e nach SPEC-0063, `config apply-roles`, `q_kind`, Suite-Registry, Patterns |
