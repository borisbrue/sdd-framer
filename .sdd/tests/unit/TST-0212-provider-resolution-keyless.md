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

## Abdeckung

CON-0186 INV-01…INV-04 · SPEC-0050 FR-01, FR-02, FR-05.
