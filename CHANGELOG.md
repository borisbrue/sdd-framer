# Changelog

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
