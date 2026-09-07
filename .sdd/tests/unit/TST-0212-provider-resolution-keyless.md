---
id: TST-0212
project: PRJ-0001
title: "Provider-Auflösung: keyfreier Default + Fail-Loud"
level: unit
spec: SPEC-0050
contract: CON-0186
status: planned
framework: pytest
artifact: "tests/unit/test_tst_0212.py"
tags: [llm, provider, factory]
---

# Test: Provider-Auflösung: keyfreier Default + Fail-Loud

> **Level:** unit · **Spec:** SPEC-0050 · **Contract:** CON-0186 · **Status:** planned

## Was wird geprüft?

Das Auflösungsverhalten von `sdd_cli.llm.factory.get_completion_provider` für die Komponente
`completion` (und die Regressionssicherung für `evaluator`).

## Testfälle

- **test_completion_defaults_to_claude_cli:** `SddConfig(raw={})` → `get_completion_provider(cfg,
  "completion")` liefert eine `ClaudeCliCompletionProvider`-Instanz (INV-01). *(RED bis Fix:
  aktueller Builtin-Default ist anthropic.)*
- **test_anthropic_optin_honored:** `raw={"llm":{"completion":{"provider":"anthropic",
  "api_key":"sk-test"}}}` → `AnthropicCompletionProvider` (INV-02; `__init__` gepatcht).
- **test_evaluator_stays_claude_cli:** `raw={"llm":{"evaluator":{"provider":"claude-cli"}}}` →
  `ClaudeCliCompletionProvider` (INV-04, Holdout-Gate-Regression).
- **test_no_silent_fallback:** `raw={"llm":{"completion":{"provider":"anthropic"}}}` ohne Key →
  Ergebnis ist KEIN `ClaudeCliCompletionProvider` (kein automatischer Provider-Wechsel, INV-03).
- **test_blueprint_config_is_keyless:** Der `llm`-Block der Blueprint-`config.yaml` setzt fuer
  keine Komponente `provider: anthropic` (FR-06). Der Fall existiert, weil FR-01 nur den
  Builtin-Default betrifft — das Blueprint liefert eine eigene Konfiguration und ueberschrieb
  den keyfreien Default fuer jedes neue Projekt wieder.
- **test_blueprint_completion_is_claude_cli:** Der wichtigste Einzelfall daraus, weil
  `completion` die meisten Aufrufer hat (FR-06).
- **test_evaluator_builtin_is_keyless:** `raw={}` -> `evaluator` loest auf
  `ClaudeCliCompletionProvider` auf (FR-07). Der Builtin stand hier auf `anthropic`, womit
  das Holdout-Gate ohne Key nicht lief.
- **test_ai_routes_builtin_is_keyless:** `raw={}` -> `ai_routes` loest auf
  `ClaudeCliCompletionProvider` auf (FR-07).
- **test_component_without_builtin_falls_back_keyless:** `local_llm` hat keinen
  Builtin-Eintrag; ohne Konfiguration greift der Fallback in `get_completion_provider`
  und muss `claude-cli` liefern, nicht `anthropic` (FR-07).

## Abdeckung

CON-0186 INV-01…INV-04 · SPEC-0050 FR-01, FR-02, FR-05, FR-06, FR-07.
