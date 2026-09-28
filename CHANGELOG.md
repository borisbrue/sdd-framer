# Changelog

## [Unreleased] – SPEC-0064: S3-Fakten mit Tasks

### Added

- Die Abnahme-Anfrage (S3) der Pipeline enthält `facts.tasks` (je Task `id`, `title`, `fr_ids`,
  `test_file`, `state`, `attempts`) und je FR in `facts.frs[].tasks` die zuständigen Task-IDs.
  Der Supervisor übernimmt `task_ids` für `reopen` von dort, statt sie aus der Historie zu erraten.
- Bei der S1-Freigabe schreibt die Pipeline die freigegebenen Tasks als `approved-tasks.json` ins
  Run-Verzeichnis (neu nach `redecompose`). Fehlt der Schnappschuss, hält der Run vor S3 mit
  Hinweis; Runs, die vor diesem Stand hinter S1 lagen, müssen neu gestartet werden.
- Golden Case `SUP-009` (zwei rote FRs, Zuordnung nur über die Fakten); SUP-004 und SUP-005
  tragen die neuen Fakten. Rolle `supervisor` 1.2.0 und `/sdd-supervise` 0.3.0 nennen sie.

### Fixed

- CON-0202 erlaubt `reopen` in `allowed_commands`; bisher verletzte jede S3-Anfrage das Schema.

## [Unreleased] – SPEC-0057: Stack-Vorlagen

### Added

- **`sdd stack list|show|apply|verify|diff|extract`**: Vorlagen richten ein Projekt für Tests mit
  FR-Markern, Qualitätsmessung und Architekturregeln ein. Quellen in dieser Reihenfolge: Projekt
  (`.sdd/stacks/`), Nutzer (`~/.config/sdd/stacks/`, `SDD_STACKS_HOME`), Blueprint.
- `apply` überschreibt nie (abweichende Dateien als `.new` mit Diff), pflegt markierte
  AGENTS.md-Abschnitte und hält Version, Quelle, Platzhalterwerte und Datei-Hashes unter `stack:`
  in `config.yaml` fest. Projekt- und Nutzervorlagen zeigen vorher eine Vorschau (`--yes`,
  `--dry-run`); `--only quality` beschränkt auf `.sdd/quality.yaml` und `.sdd/quality/`.
- `verify` prüft Werkzeuge, Sonden, mindestens einen FR-markierten Test, `sdd arch check` und die
  Prüfpunkte der Vorlage; `diff` vergleicht Projekt, angewendeten Stand und aktuelle Vorlage;
  `extract` macht aus einem Projekt eine eigene Vorlage.
- **`sdd init --stack NAME`** und die Blueprint-Vorlagen **`python-cli`** und **`python-fastapi`**
  (Schichten mit ADR und Regel, Skeleton-Test mit FR-Marker).
- `sdd config validate` prüft die Regelgruppe `stack`.

### Changed

- **`sdd quality init --preset X`** schreibt nichts mehr, sondern nennt
  `sdd stack apply <vorlage> --only quality` (`python` → `python-cli`) und endet mit Exit 1.
  `blueprint/presets/` entfällt; das Preset `python` lebt in der Vorlage `python-cli` weiter.

## [Unreleased] – SPEC-0063: Benchmark-Suite e2e und Pipeline-Budget

### Added

- Suite-Art **`e2e`** für `sdd bench run`: ganze Specs eines Fixtures per `sdd pipeline run --auto`
  in einer Git-Kopie umsetzen, Messung mit versteckten Akzeptanztests (FR-Marker) und
  `sdd quality measure`; Tokens je Rolle aus der Usage der Runs. Isolation als Strategie (`dir`).
- Fixture **`todo-service`** im Blueprint (Python-Standardbibliothek, Schichten, drei Specs mit
  3/6/10 FRs, versteckte Tests, Referenzlösung) und `bench/suites/e2e.yaml`.
- **Pipeline-Budget**: `pipeline.budget` bzw. `--max-tokens`/`--max-claude-tokens`; der Run hält mit
  Grund `budget`. `sdd config validate` prüft die Werte.

### Changed

- Der Bench-Report nennt je Eintrag die Zahl der Läufe je Ausgang.
- `sdd arch check` validiert Sonden-Ausgaben gegen den Zweig ihres Formats (Validator gecacht) und
  `edges[].to` ohne `oneOf` (gleichwertig); hält die Laufzeitgrenze aus CON-0209 auch im Container.

## [Unreleased] – SPEC-0056: Benchmark-Strecke

### Added

- **`sdd bench init|run|report|compare`**: Modellbelegungen über Suiten vergleichen. Matrix mit
  Belegungen, Varianten (`profil@variante`), Sweep, Wiederholungen, Stufenmodell `top_k` und
  Budget; `--dry-run`, `--resume`. Suite-Arten `roles` (Rollen-Evals, `q_kind: eval`) und `regen`
  (Module aus Unit-Tests neu schreiben, `q_kind: quality`), erweiterbar über eine Registry.
- Report mit Q ± Streuung, Tokens je Rolle und gesamt (geschätzte markiert), Effizienz, Tokens je
  erfüllter Anforderung, Pareto-Front mit und ohne Claude-Tokens, Signifikanzhinweis; HTML mit
  Streudiagramm. `compare` warnt bei getauschtem Servermodell.
- **`sdd config apply-roles`**: Belegung aus einem Benchmark mit Diff als `llm.roles` übernehmen.
- Profil-Schlüssel `max_concurrent` und `seed` (an `openai-compat`); `bench/results/` in den
  lokalen Ignores; `bench/suites/regen.yaml` mit sieben Modulen aus BEFUND-modelle §3.

### Changed

- `pipeline.facade` bietet `run_role`, `role_binding` und `measure_changed`; `EvalRunner` nimmt
  Provider-Hüllen (`wrap`) an. SPEC-0063 (Suite `e2e`) ist als Folge-Spec angelegt.

## [Unreleased] – SPEC-0055: Rollen-Evals mit Golden Cases

### Added

- **`sdd role eval|compare|accept`** und **`sdd role case new|capture|confirm`**: Rollen gegen
  Golden Cases messen (Score, Streuung, `pass@1`, `pass^k`, Tokens je Fall), Kandidaten nach der
  Ratchet-Regel vergleichen und übernehmen (Version, `baseline.json`, Rollen-CHANGELOG).
- Golden Cases im Blueprint: je Pipeline-Rolle 8 Fälle, davon 3 Holdout unter
  `.sdd/holdout/roles/`; `sdd init`/`sdd upgrade` installieren fehlende Fälle.
- Check-Registry `pipeline/checks.py` mit Kontexten (`gate`, `eval`), Parametern und Score; neue
  Checks u. a. `task_count`, `ordered_before`, `max_complexity`, `fr_marker_present`,
  `red_against_stub`, `green_against_reference`, `mutation_kill_rate`, `paths_allowed`,
  `hidden_tests_pass`, `arch_violations`, `quality_score`, `seeded_bug_recall`,
  `clean_diff_precision`, `decision_matches`, `reason_mentions`.
- Rolle **`judge`** (`llm.roles.judge`, Default `claude-cli`): bewertet Rubriken blind und ersetzt
  die Komponente `evaluator` in `sdd quality --judge`.
- Skill **`/sdd-role-tune`**; Profil-Schlüssel `requests_per_minute`.

### Changed

- Alle Scanner von `.sdd/holdout/` lassen `.sdd/holdout/roles/` aus; Rollendateien dürfen nur
  gate-fähige Checks nennen (`sdd validate`).
- Das Run-Protokoll nennt gescheiterte Checks eines Rollenaufrufs (`failed_checks`).

## [Unreleased] – SPEC-0062: Ein Ausführungspfad

### Added

- `sdd pipeline run --session ROLLE` (mehrfach): Rollen nur für diesen Run im Modus `session`,
  `config.yaml` bleibt unverändert; `--steps holdout,finalize,automerge` ersetzt
  `pipeline.auto_steps` für einen Run mit `--auto`. Beides steht unter `options` in `run.json`.
- `sdd upgrade` migriert `task_routing` und `llm.local_llm`: Profil `llm.profiles.lokal`,
  `llm.roles.implementer.by_complexity` für die Stufen mit Score ≤ Schwelle (low 15, medium 50,
  high 80); die alten Blöcke werden mit `# [SPEC-0062]` auskommentiert. Bestehende Einträge werden
  nicht überschrieben, sondern gemeldet.
- Architekturregel ARCH-05 (ADR-0006) mit Schicht `pipeline`: Interna der Pipeline nur in
  `pipeline` und `entry`, sonst `pipeline.facade`.

### Changed

- `/sdd-implement` 1.0.0: Vorbedingungen, Review, Holdout-Anlage, dann
  `sdd pipeline run SPEC --auto --session test_author --session implementer --session supervisor`
  und Abarbeiten der Anfragen mit `sdd pipeline done`/`decide`. Repo-Kopie und Blueprint sind gleich.
- Web-UI: `POST /api/orchestrate` und `/api/pipeline/*` sind ein Adapter vor
  `sdd pipeline run --auto` (Prozess; `dry_run` → `--dry-run`, `no_pr` → `--steps holdout`); neu
  sind die Status `paused` und `aborted` (CON-0021 0.4.0). `orchestrate` in `/api/sdd/run` und im
  Chat startet ebenfalls die Pipeline.
- `sdd start --auto` und `sdd maintenance --auto-pr` starten `sdd pipeline run --auto`.
- GitHub-Action-Vorlage ruft `sdd pipeline run $SPEC --auto`; `ANTHROPIC_API_KEY` ist optional.

### Removed

- `task_routing/`, `orchestrator.py`, `llm_probe.py` und der CodeGen-Pfad (`CodeGenProvider`,
  `get_code_gen_provider`, `ClaudeCliCodeGenProvider`, `OpenAICompatCodeGenProvider`).
  `sdd orchestrate`, `sdd task-route`, `sdd task-exec` und `sdd task-loop` sind Verweise (Exit 1).
  Python unter `tool/`: 33 200 → 31 289 Zeilen (−1 911), Tests netto −1 869.
- SPEC-0045 (CON-0171 bis CON-0174) sowie CON-0012, CON-0024, CON-0033, CON-0063, CON-0113 und
  CON-0164 sind deprecated.

## [Unreleased] – SPEC-0061: Pipeline-Fähigkeiten

### Added

- Arbeitsrollen im Modus `session` (`llm.roles.<rolle>.mode: session`): Auftrag in
  `pending-work.json`, Exit 3, Bestätigung mit **`sdd pipeline done RUN [--json]`**. Rollenvertrag:
  PathPolicy, Gates und Eskalation gelten wie bei Modellen.
- `llm.profiles` (benannte Modelle) und `llm.roles.<rolle>.profile` / `.by_complexity`
  (`low|medium|high` → Profil oder `session`).
- `sdd pipeline run --task ID` (ein Task der gespeicherten Zerlegung) und `--auto`
  (Abschluss-Kette aus `pipeline.auto_steps`: `holdout` vor S3 als Fakt, `finalize`, `automerge`
  nach Autonomie-Level). S3 kennt `reopen` (Tasks mit Hinweis erneut öffnen, `pipeline.max_reopen`).
- Gates pro Task (`pipeline.task_gates`: `tests`, `architecture`, `lint`); Task-Typen `test`,
  `config`, `doc` ohne RED-Zwang.

### Changed

- `sdd config test-llm` prüft Rollen und Profile (`--role`, `--profile`) statt des abgelösten
  `llm_pool`; `--id` entfällt.
- Default-Rolle `supervisor` 1.1.0 (kennt `reopen`); lokal angepasste Rollen bekommen beim
  `sdd upgrade` eine `supervisor.md.new`.

## [Unreleased] – SPEC-0058: Rückbau abgelöster Ausführungspfade und Pipeline-Monitor

### Removed

- `sub_agent.py`, `local_agent.py`, `autopilot.py` (nie angebunden; `local_agent` setzte als
  einziger Code `ANTHROPIC_API_KEY`/`ANTHROPIC_BASE_URL`), `dist_orchestrator.py`,
  `review_pipeline.py`, `llm_pool.py`, `dag_command.py`, `dag_event.py` samt Tests.
- **`sdd distribute`** ist ein versteckter Verweis auf `sdd pipeline run` (führt nichts aus, Exit 1).
- Wizard-Abschnitt `llm` (LLM-Pool) und die `llm_pool`-Regeln in `sdd config validate`.
  Migration: `sdd upgrade` kommentiert die Blöcke `llm_pool`, `local_agent` und `autopilot` in
  `config.yaml` aus (`# [SPEC-0058] …`) und meldet sie.

### Added

- `sdd spec deprecate SPEC-XXXX --reason … [--replaced-by …] [--keep CON-…]` und
  `sdd contract deprecate CON-XXXX --reason …`: Ablösen über die CLI mit Audit-Eintrag.
- `sdd pipeline status RUN --json`; Leseschnittstelle `sdd_cli.pipeline.monitor`.
- `sdd_cli.llm.claude_available()` für Verfügbarkeitsprüfungen außerhalb der LLM-Schicht.

### Changed

- Der Monitor der Web-UI (`/api/orchestrate/runs`, `/stream/{run_id}`) zeigt Runs von
  `sdd pipeline run` (Format unverändert); die Befehls-Route antwortet mit 410.
- Web-Routen `/specs/{id}/implement` und `/evaluate` starten `sdd pipeline run` bzw.
  `sdd holdout run` statt der entfernten Befehle.
- Die Tabelle `token_usage` ist in `sdd_cli.llm.usage_table` definiert (ARCH-02).
- SPEC-0026, SPEC-0035, SPEC-0036 und SPEC-0037 sind `deprecated`.

## [Unreleased] – SPEC-0059: Architekturregeln und ADRs für sdd-framer (Dogfooding)

### Added

- `.sdd/architecture.yaml` mit den Regeln ARCH-01 bis ARCH-04 und den ADRs ADR-0002 bis ADR-0005
  (CLI einziger Schreiber, Schichtrichtung, Provider nur über die Factory, `claude` nur im
  Provider). Bekannte Altlasten stehen mit Grund und Ziel-Spec in `.sdd/quality/arch-baseline.json`.
- `.sdd/quality.yaml` (Preset `python`, angepasst: nur `tool/**`, Werkzeuge aus `.venv/bin/`).
- `write_ownership` kennt `unresolved: skip|violation` (CON-0208): Schreibzugriffe mit variablem
  Ziel können als Verstoß zählen.
- Pre-Commit-Hook (`sdd install-hooks`) führt `sdd arch check` aus, wenn `.sdd/architecture.yaml`
  existiert und `.py`-Dateien gestaged sind; `quality.arch_pre_commit: false` schaltet das ab.
- `sdd arch check` zeigt bei Baseline-Treffern die Spec, die sie behebt (`warn (Baseline, SPEC-0058)`).

### Changed

- Rollen-Provider der Pipeline entstehen in der Factory (`llm.factory.get_role_provider`);
  `pipeline/providers.py` importiert nichts mehr aus `llm/providers/`.

## [Unreleased] – SPEC-0053: Rollenbasierte Pipeline mit Claude als Supervisor

### Added

- **`sdd pipeline run SPEC [--dry-run] [--resume RUN] [--max-tasks N]`**, **`decide`**,
  **`status`**, **`report`**: Rollen `decomposer`, `test_author`, `implementer`, `reviewer` arbeiten
  über ihre Modelle; der Supervisor entscheidet nur an S1 (Zerlegung), S2 (Eskalation) und S3
  (Abnahme). Run-Verzeichnis `.sdd/runs/<SPEC>/<run_id>/` mit `run.json`, `state.json`,
  `events.jsonl`, `decisions.jsonl`, `pending-decision.json`.
- Rollen als Dateien `.sdd/roles/<rolle>.md` (Frontmatter nach CON-0199, Body = System-Prompt);
  `sdd init` legt sie an, `sdd upgrade` ergänzt fehlende und legt bei lokal geänderten
  `<rolle>.md.new` daneben.
- `llm.roles.<rolle>` wählt das Modell je Rolle (Fallback: `legacy_component` der Rolle, dann
  `claude-cli`); `llm.roles.supervisor.mode: inline|session`. `sdd config validate` warnt bei
  ignorierten Parametern und wenn der Reviewer dasselbe Modell nutzt wie Implementer/Test-Autor.
- PathPolicy (CON-0204): Default deny; nur `test_author` (Testdatei) und `implementer`
  (`allowed_paths`) schreiben. Auch der CodeGen-Pfad von `openai-compat` nutzt sie.
- Skill **`/sdd-supervise`**: Claude Code als Supervisor im Dialog (`mode: session`).

### Changed

- `sdd decompose` holt Provider und Prompt aus der Rolle `decomposer`; Tasks tragen `fr_ids` und
  `allowed_paths` (Task-Schema additiv erweitert, CON-0203).
- `openai-compat` schützt `tests/` im CodeGen-Pfad nicht mehr pauschal; maßgeblich ist die
  PathPolicy (`.sdd/`, `specs/`, `contracts/`, `pipeline.protected_paths`).

## [Unreleased] – SPEC-0060: Usage-Erfassung aller LLM-Provider

### Changed

- Jeder Provider aus `get_completion_provider`/`get_code_gen_provider` ist vom Usage-Decorator
  umhüllt (`sdd_cli.llm.usage`): jeder Aufruf erzeugt genau einen Datensatz in `token_usage`,
  auch bei Fehlern. Den ursprünglichen Provider liefert `sdd_cli.llm.usage.unwrap()`.
- `claude-cli` liest Tokens, Cache, Thinking-Tokens, Modell und `stop_reason` aus dem
  JSON-Envelope; `openai-compat` zusätzlich Reasoning-Tokens, `finish_reason` und Servermodell.
  `CompletionResult.usage` ist nie mehr `None`, `UsageMetadata.source` sagt `reported`,
  `estimated` oder `unavailable`.
- `CodeGenProvider.generate()` liefert `CodeGenResult` (weiter als `(files, explanation)`
  entpackbar, plus `.usage`).
- `token_usage` bekommt die Spalten `reasoning_tokens`, `finish_reason`, `server_model`,
  `source`, `run_id`, `context_json` (additive Migration). `sdd token-history` zeigt
  Reasoning-Tokens, `--export` alle neuen Spalten.
- `sdd estimate`, `sdd calibrate`, `token-history` und die Web-Zusammenfassung zählen Aufrufe
  ohne Usage (`source: unavailable`) nicht mit und nennen ihre Anzahl.
- Die Web-API speichert Usage in `token_usage` statt in `.sdd/ai_usage.json`.
  Migration: `sdd upgrade` übernimmt `ai_usage.json` einmalig (Kontext `origin: web`) und
  benennt die Datei in `ai_usage.json.migrated` um.

## [Unreleased] – SPEC-0044: CLI & Skill Consolidation

### Removed

- **`sdd pattern`** group (`pattern accept`, `pattern reject`, `pattern list`) removed.
  Migration: Pattern-Vorschläge werden automatisch im `/sdd-review`-Skill verarbeitet.

- **`sdd dev`** group (`dev start`, `dev exec`, `dev close`, `dev pr`, `dev build`,
  `dev push`, `dev up`, `dev down`) removed as public CLI commands.
  Migration: Interne `DevContainerManager`-Klasse bleibt erhalten; `sdd start` und
  `sdd finalize` sind die öffentlichen Einstiegspunkte für den Entwicklungs-Lifecycle.

- **`sdd pattern-suggest`** top-level command removed (war Teil des Pattern-Flows).

- **`sdd implement`** stub removed (war nie implementiert; `sdd start` + `/sdd-implement`).

- **`sdd new agents-md`** and **`sdd new github-workflow`** removed; in `sdd init` integriert.

- **`sdd status-check`** aus öffentlicher CLI entfernt (bleibt interner pre-commit-Hook).

### Added

- **`sdd review`** group: `sdd review spec`, `sdd review contract`, `sdd review pending`
- **`sdd holdout`** group: `sdd holdout generate`, `sdd holdout run`
- **`sdd autonomy`** group: `sdd autonomy level`, `sdd autonomy set-level`, `sdd autonomy false-positive`
- **`sdd spec solid`** and **`sdd spec regression`** as subcommands under `sdd spec`
- **`sdd test generate`** for creating TST stubs from approved contracts
- **`sdd new hotfix`** for lightweight hotfix tracking
- **`sdd contract analyze`** (renamed from `sdd contract review`)
- Skill frontmatter `scope:` field added to all `.claude/commands/sdd-*.md` files

### Changed

- `sdd upgrade` now mentions Skill-file retrofit in its help text
- `/sdd` skill overview updated to list all available skills without duplicates
