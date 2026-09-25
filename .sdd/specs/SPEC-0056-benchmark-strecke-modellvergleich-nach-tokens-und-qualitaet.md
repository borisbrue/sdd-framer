---
id: SPEC-0056
title: "Benchmark-Strecke: Modellvergleich nach Tokens und Qualität"
type: feature
status: draft
owner: "Boris"
created: 2026-09-25
updated: 2026-09-25
version: 0.1.0
priority: high
tags: [benchmark, llm, local-llm, metrics, token-tracking, quality]
depends_on: [SPEC-0053, SPEC-0054, SPEC-0055]
contracts: []
tests: []
---

# Benchmark-Strecke: Modellvergleich nach Tokens und Qualität

> **Status:** draft · **Owner:** Boris · **Version:** 0.1.0

## 1. Kontext & Motivation

Die Modellwahl erfolgt heute aus einmaligen, handgeschriebenen Untersuchungen
(BEFUND-modelle-2026-09-24). Die Skripte dazu liegen nicht im Repo, die Ergebnisse sind nicht
wiederholbar, und sie messen isolierte Codeaufgaben, nicht das Verhalten in der
sdd-Pipeline. Welche Kombination aus Modellen und Rollen **pro verbrauchtem Token** die beste
Codequalität, Architekturtreue und Anforderungserfüllung liefert, lässt sich nicht beantworten.

Diese Spec macht daraus eine wiederholbare Strecke im Repo. Sie nutzt die Pipeline (SPEC-0053) als
Prüfling, die Qualitätsmessung (SPEC-0054) als Messgerät und die Rollen-Evals (SPEC-0055) als
schnelle Vorstufe.

## 2. Zielsetzung

**Primärziel:** `sdd bench run` vergleicht beliebige Modellbelegungen über eine feste Aufgabenmenge
und zeigt je Belegung Qualität (drei Dimensionen) gegen Tokenverbrauch (Input, Output, Reasoning)
inklusive Pareto-Front.

**Erfolgskriterien (messbar):**
- [ ] Die Methode von BEFUND-modelle §3 (Module aus Tests regenerieren) ist als Suite `regen`
      reproduzierbar: Zwei Läufe mit gleicher Konfiguration unterscheiden sich im Mittel um höchstens
      die gemessene Streuung.
- [ ] Ein Report beantwortet für jede Rolle: welches Profil hat die höchste Qualität, welches das
      beste Verhältnis Qualität/Token, und welche Profile liegen auf der Pareto-Front.
- [ ] Jede Kennzahl im Report ist bis zum einzelnen Lauf (`events.jsonl`, Quality-Report)
      zurückverfolgbar.
- [ ] Ein Benchmark-Lauf verändert weder das Projekt-Worktree noch `.sdd/` des Projekts.

**Nicht-Ziele (explizit):**
- Kein öffentliches Leaderboard, kein Upload von Ergebnissen.
- Kein Hosting oder Laden von Modellen; die Endpunkte müssen laufen.
- Keine reinen Durchsatzmessungen (TTFT, tok/s, Prefill), außer als Nebenmetrik aus den
  Pipeline-Läufen. Dafür bleibt `sdd config test-llm` zuständig.

## 3. Architektur & Design Patterns

### Suite → Aufgabe → Lauf
```
bench/
├── suites/
│   ├── roles.yaml        # Stufe 1: Golden Cases aus SPEC-0055 (billig, schnell)
│   ├── regen.yaml        # Stufe 2: Module aus versteckten Tests regenerieren (BEFUND §3)
│   └── e2e.yaml          # Stufe 3: ganze Spec per `sdd pipeline run` auf Fixture-Projekt
├── fixtures/
│   └── todo-service/     # kleines Referenzprojekt: .sdd/, AGENTS.md, architecture.yaml,
│                         # Specs, Contracts, versteckte Akzeptanztests, Referenzlösung
├── matrix.yaml           # welche Profile in welcher Rolle, Wiederholungen, Parameter-Varianten
└── results/<ts>/         # results.jsonl, report.md, report.html, runs/<lauf-id>/…
```

`matrix.yaml`:
```yaml
suite: e2e
repetitions: 3
profiles: [qwen35-a3b-mlx, qwen38-27b, gpt-oss-120b, claude-cli]   # aus llm.profiles
assignments:                          # je Zeile eine Belegung (Kandidat)
  - name: all-qwen38
    roles: { decomposer: qwen38-27b@think, test_author: qwen38-27b, implementer: qwen38-27b,
             reviewer: qwen35-a3b-mlx, supervisor: claude-cli }
  - name: gptoss-decompose
    roles: { decomposer: gpt-oss-120b@high, implementer: qwen38-27b, "*": qwen35-a3b-mlx,
             supervisor: claude-cli }
variants:                             # Profil-Suffixe
  think: { thinking: true }
  high:  { reasoning_effort: high }
sweep:                                # optional: kartesisches Produkt für eine Rolle
  role: implementer
  profiles: [qwen35-a3b-mlx, qwen38-27b, gpt-oss-120b]
```

### Stufenmodell (Kosten sparen)
Stufe 1 (Rollen-Evals) filtert Profile je Rolle vor. Nur die besten `top_k` je Rolle gehen in
Stufe 2 und 3. Der Report weist die Filterung aus.

### Messung pro Lauf
Jeder Lauf erzeugt einen `BenchRecord`:
- **Kosten:** Tokens je Rolle (Input, Output, Reasoning), Aufrufe, Fehlversuche,
  Supervisor-Eingriffe, Eskalationen, Wandzeit.
- **Qualität:** der Quality-Report aus SPEC-0054 auf dem Endstand, gemessen gegen versteckte Tests
  und die Referenz-`architecture.yaml`.
- **Ausgang:** `completed`, `halted` oder `error`.

Ein Lauf, der anhält, zählt mit dem erreichten Stand; es gibt keinen Ausschluss aus der Wertung.

### Kennzahlen
- `Q`: Gesamtscore nach SPEC-0054 (Gewichte aus der Suite, Default 0,5 / 0,25 / 0,25).
- `Q_req`, `Q_arch`, `Q_code`: Teilscores.
- `T`: Gesamttokens, zusätzlich `T_in`, `T_out`, `T_reason` und `T_claude` (Anteil Supervisor).
- Effizienz: `Q / (T / 1e5)` und **Tokens je erfülltem FR**.
- Stabilität: Standardabweichung von `Q` über Wiederholungen, `pass^k` der Anforderungen.
- Pareto-Front über (Q ↑, T ↓), getrennt nach „mit Claude-Tokens“ und „nur lokale Tokens“.

### Template Method: `BenchTask`
`prepare(workspace)` → `run(assignment)` → `measure()` → `teardown()`. Jede Suite-Art
implementiert nur `prepare` und `run`. Messung und Protokoll sind gemeinsam.

## 4. Funktionale Anforderungen

- **FR-01:** `sdd bench run --matrix bench/matrix.yaml [--suite NAME] [--only ASSIGNMENT]
  [--repetitions N] [--concurrency N] [--dry-run]` führt die Matrix aus und schreibt nach
  `bench/results/<ts>/`. `--dry-run` zeigt Zahl der Läufe, geschätzte Tokens (aus früheren
  Ergebnissen oder `sdd estimate`) und geschätzte Dauer.
- **FR-02:** Jede Aufgabe läuft in einem frischen Arbeitsverzeichnis (git worktree bzw. kopiertes
  Fixture), optional im Dev-Container (`bench.isolation: dir|container`, Default `dir`). Versteckte
  Tests und Referenzlösung werden erst zur Messung in das Verzeichnis kopiert, nach Abschluss aller
  Rollenaufrufe. Kein Rollenkontext enthält sie.
- **FR-03:** Suite `roles` führt `sdd role eval` (SPEC-0055) für jede Rolle × jedes Profil aus und
  übernimmt die Ergebnisse als `BenchRecord` mit `Q = Eval-Score`.
- **FR-04:** Suite `regen` entfernt die in der Suite gelisteten Module aus einer eingefrorenen
  Kopie eines Projekts (Default: sdd-framer zu einem festen Commit). Die Rolle `implementer`
  erzeugt sie aus den vorhandenen Unit-Tests neu; gemessen wird mit den Tests und SPEC-0054 auf
  den regenerierten Dateien.
- **FR-05:** Suite `e2e` führt `sdd pipeline run` (SPEC-0053) für die gelisteten Specs eines Fixture-
  Projekts mit der jeweiligen Belegung aus und misst den Endstand mit
  `sdd quality measure --spec … --diff <start>` plus versteckten Akzeptanztests.
- **FR-06:** Jeder Lauf schreibt einen `BenchRecord` nach `results.jsonl`
  (Schema `bench-record.schema.json`) mit allen Kennzahlen aus Abschnitt 3, der Belegung,
  Profilparametern, Rollenversionen, Suite-Version, sdd-Version, Git-SHA des Fixtures, Endpunkt,
  vom Server gemeldetem Modellnamen und Zeitstempeln.
- **FR-07:** `sdd bench report <ergebnisordner> [--html] [--by role|assignment]` erzeugt:
  - Tabelle je Belegung: Q, Q_req, Q_arch, Q_code (Mittel ± Std), T_in, T_out, T_reason,
    T_claude, Tokens je erfülltem FR, Fehlversuche, Eingriffe.
  - Je Rolle (aus `sweep` oder Stufe 1): Rangliste der Profile nach Q und nach Effizienz.
  - Pareto-Diagramm Q gegen T (HTML: interaktiv, Markdown: Tabelle der Front).
  - Signifikanzhinweis: Unterschiede kleiner als die gepoolte Standardabweichung werden als
    „nicht unterscheidbar“ markiert.
- **FR-08:** `sdd bench compare <ergebnis-a> <ergebnis-b>` vergleicht zwei Benchmark-Läufe, etwa vor
  und nach einer Rollen-Änderung oder einem Modell-Update, je Belegung mit Delta und
  Signifikanzhinweis.
- **FR-09:** Reproduzierbarkeit:
  - Jeder LLM-Aufruf trägt einen Cache-Nonce.
  - `seed` wird gesetzt, sofern der Provider ihn unterstützt.
  - Rate-Limits und parallele Anfragen werden je Profil beachtet (`rate_limit_per_minute`,
    `max_concurrent`).
  - Nach einem Abbruch setzt `--resume <ergebnisordner>` die fehlenden Läufe fort.
- **FR-10:** Der Blueprint liefert die Suiten `roles` und `regen` sowie das Fixture `todo-service`
  mit mindestens drei Specs unterschiedlicher Größe (klein: 3 FRs, mittel: 6 FRs, groß: 10 FRs
  mit Schichtregeln) samt versteckten Akzeptanztests und Referenzlösung.
- **FR-11:** Die Ergebnisse von `sdd bench` können als Empfehlung in `config.yaml` übernommen werden:
  `sdd bench apply <ergebnisordner> --assignment NAME` schreibt die Belegung als
  `llm.roles`-Block (mit Rückfrage und Diff; ohne `--yes` keine Änderung).

## 5. Nicht-funktionale Anforderungen

| Kategorie         | Anforderung                                                               |
|-------------------|---------------------------------------------------------------------------|
| Isolation         | Kein Lauf verändert das Projekt; `bench/results/` ist per `.gitignore` ausgeschlossen, Reports können gezielt eingecheckt werden. |
| Geheimnisse       | API-Keys stehen nur in Env-Variablen oder `~/.config/sdd/*.env`, nie in `results.jsonl` oder Reports. |
| Keyfreiheit       | Claude nur über `claude-cli`; der Benchmark verlangt keinen `ANTHROPIC_API_KEY`. |
| Kostenkontrolle   | `bench.budget.max_tokens` und `max_claude_tokens` brechen einen Lauf kontrolliert ab (Ausgang `halted: budget`). |
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
    Given die Suite e2e mit Fixture todo-service
    When ein Lauf die Rolle implementer aufruft
    Then enthält kein Rollenkontext Dateien aus den versteckten Akzeptanztests

  Scenario: Budget
    Given bench.budget.max_claude_tokens ist 50000
    When ein Lauf 50000 Claude-Tokens überschreitet
    Then endet der Lauf mit halted: budget
    And der BenchRecord enthält den bis dahin gemessenen Stand
```

## 7. Edge Cases & Fehlerfälle

- Endpunkt fällt mitten im Lauf aus: Lauf endet mit `error`, wird bei `--resume` wiederholt und
  zählt nicht doppelt.
- Modell auf dem Server ausgetauscht (gleicher Name, andere Quantisierung): Der vom Server
  gemeldete Modellname und, soweit verfügbar, Metadaten (`/v1/models`) werden im Record
  gespeichert. `compare` warnt bei Abweichung.
- Thinking-Modelle erzeugen sehr viele Reasoning-Tokens: `T_reason` wird getrennt ausgewiesen und
  optional in der Effizienz ausgeklammert (`--exclude-reasoning`), um den Einfluss sichtbar zu machen.
- Provider liefert keine Usage: Tokens werden mit dem Tokenizer-Schätzer ermittelt und als
  `estimated: true` markiert. Im Report werden solche Werte mit Sternchen gekennzeichnet.

## 8. Contracts (was wird garantiert)

| Contract-ID | Typ      | Was wird garantiert?                                           |
|-------------|----------|----------------------------------------------------------------|
| CON-XXXX    | data     | `bench-matrix.schema.json` (Matrix, Belegungen, Varianten, Sweep) |
| CON-XXXX    | data     | `bench-suite.schema.json` (Suite und Aufgaben)                 |
| CON-XXXX    | data     | `bench-record.schema.json`                                     |
| CON-XXXX    | behavior | Kennzahlen-Formeln, Pareto-Bestimmung, Signifikanzhinweis      |
| CON-XXXX    | behavior | Isolation versteckter Tests und Referenzlösungen               |

## 9. Tests (wie wird verifiziert)

| Test-ID  | Level       | Was prüft der Test?                                                |
|----------|-------------|--------------------------------------------------------------------|
| TST-XXXX | unit        | Kennzahlen, Pareto-Front, Signifikanzmarkierung aus Fixture-Records |
| TST-XXXX | unit        | Matrix-Expansion (Varianten, Sweep, `*`-Belegung)                  |
| TST-XXXX | integration | `sdd bench run` mit FakeProvidern auf Mini-Suite, Resume, Budget   |
| TST-XXXX | acceptance  | Gherkin-Szenarien aus Abschnitt 6                                  |

## 10. Offene Fragen

- [ ] Welches Fixture-Projekt ist realistisch genug? Vorschlag: `todo-service` (Python, FastAPI,
      Schichten Domain/Service/API/Persistenz) plus die Suite `regen` auf sdd-framer. Optional
      später sddit (Rust) als zweites e2e-Fixture, wenn der Rust-Adapter aus SPEC-0054 existiert.
- [ ] Wo laufen die Benchmarks dauerhaft: lokal gegen den MLX-Server (192.168.0.149) und/oder gegen
      mittwald (LiteLLM → vLLM)? Beides ist über Profile möglich; Default-Profile im Blueprint
      bleiben leer.
- [ ] Soll eine GitHub-Action den Benchmark nächtlich gegen einen selbst gehosteten Runner fahren?

## 11. Änderungshistorie

| Datum      | Version | Autor         | Änderung            |
|------------|---------|---------------|---------------------|
| 2026-09-25 | 0.1.0   | Boris, Claude | Initiale Erstellung |
