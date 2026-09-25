# Changelog

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
