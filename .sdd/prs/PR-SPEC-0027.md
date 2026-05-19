# PR: feat(SPEC-0027) – Geführte SDD-Projektkonfiguration

**Branch:** feat/SPEC-0027 → main
**Commit:** d7c4087
**Status:** bereit zum Merge (Docker nicht verfügbar → lokales PR-Dokument)

## Summary

- `config_manager.py` — Dot-Notation `set/get/show/validate` + atomares YAML-Schreiben
- `llm_probe.py` — LlmProviderProbe-Strategien (Ollama, Anthropic, OpenAI-compat)
- `config_wizard.py` — Interaktiver Builder-Wizard mit Section-Routing + CI/CD non-interactive
- `main.py` — `sdd config wizard/set/get/show/validate/test-llm` Command-Group
- `.claude/commands/sdd-config.md` — `/sdd-config` Claude-Code-Skill
- 6 Contracts (CON-0102–0107), 6 TST-Dokumente (TST-0121–0126), 46 Tests

## Test-Ergebnis

881 passed, 12 skipped — lokale pytest-Ausführung (Docker nicht verfügbar)

## Merge-Anweisung

```bash
git checkout main
git merge feat/SPEC-0027 --no-ff
```
