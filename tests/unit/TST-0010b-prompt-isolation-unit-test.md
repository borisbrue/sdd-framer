---
id: TST-0010b
project: ""
title: "Prompt-Isolation-Unit-Test"
level: unit
spec: SPEC-0004
contract: CON-0009
status: planned
framework: "pytest"
artifact: "tests/unit/test_prompt_isolation.py"
tags: ["orchestrator", "holdout", "isolation", "dark-factory"]
---

# Test: Prompt-Isolation-Unit-Test

> **Level:** unit · **Spec:** SPEC-0004 · **Contract:** CON-0009 · **Status:** planned

## Was wird geprüft?

Maschinelle Verifikation von CON-0009 / US-01 Acceptance Criteria:
Der von `orchestrator.py` erzeugte Code-Generierungs-Prompt enthält **keinen** Dateiinhalt
aus `.sdd/holdout/` — unabhängig davon, wie viele HOL-Dokumente dort existieren.

Der Test liest den Prompt-String direkt aus `_build_code_gen_prompt()` und prüft,
dass kein HOL-Titeltext, kein HOL-Body und keine HOL-ID im erzeugten String erscheint.

## Vorbedingungen

- `sdd-cli` installiert (kein LLM-Call nötig — nur `_build_code_gen_prompt()` testen)
- `pytest` mit `tmp_path`-Fixture

## Ablauf

### TC-01: HOL-Inhalte erscheinen nie im Prompt

1. Lege drei HOL-Dokumente in `.sdd/holdout/` an mit bekannten Titles und Bodies
2. Rufe `_build_code_gen_prompt(spec_content, agents_md, contracts, "")` direkt auf
3. Prüfe für jedes HOL-Dokument: Titel und Body **nicht** im erzeugten Prompt enthalten
4. Prüfe: Spec-Inhalt **ist** im Prompt enthalten (positive Assertion)

### TC-02: Contracts sind im Prompt enthalten

1. Erstelle einen Contract mit bekanntem Inhalt
2. Rufe `_build_code_gen_prompt(spec_content, agents_md, [(cid, contract_content)], "")` auf
3. Prüfe: Contract-Inhalt im Prompt enthalten
4. Prüfe: kein HOL-Inhalt enthalten

### TC-03: AGENTS.md ist im Prompt enthalten, HOL nicht

1. Füge AGENTS.md-Inhalt als `agents_md`-String ein
2. Prüfe: AGENTS.md-Inhalt im Prompt
3. Prüfe: kein HOL-Inhalt im Prompt

### TC-04: Leeres Holdout-Verzeichnis — kein Fehler

1. Kein `.sdd/holdout/`-Verzeichnis (oder leer)
2. Prompt-Bau läuft fehlerfrei
3. Prompt enthält Spec + AGENTS.md + Contracts

### TC-05: Fehler-Kontext aus vorherigem Attempt enthält keine HOL-Inhalte

1. Baue `prev_error_context` als String ohne HOL-Inhalte
2. Prüfe: Prompt enthält `prev_error_context`
3. Prüfe: HOL-Titeltext erscheint nur dann, wenn er explizit im Fehlerkontext steht
   (dieser Fall liegt **nicht** vor — Fehlerkontext kommt vom Evaluator, nicht von HOL)

## Erwartetes Ergebnis

Alle 5 Test-Cases bestehen. Kein HOL-Inhalt erscheint im Prompt, da
`_build_code_gen_prompt()` per Allowlist-Prinzip aufgebaut ist.

## Verknüpfung mit Contract

- CON-0009 G-01: Holdout-Verzeichnis existiert in `.sdd/holdout/` (Voraussetzung)
- CON-0009 INV-01: Allowlist-Prinzip — Prompt enthält nur Spec + AGENTS.md + Contracts

## Hinweise zur Implementierung

```python
from sdd_cli.orchestrator import _build_code_gen_prompt

SPEC_CONTENT  = "# Test Spec\nImplementiere Login-Feature"
AGENTS_CONTENT = "## Service-Zweck\nAuth-Service"
CONTRACT_CONTENT = "# CON-0001\nHTTP POST /api/auth/login"
HOL_TITLE   = "GEHEIMER_HOL_TITEL_XYZZY"
HOL_BODY    = "Given ein Nutzer mit secret_password_abc"

def test_holdout_not_in_prompt():
    contracts = [("CON-0001", CONTRACT_CONTENT)]
    prompt = _build_code_gen_prompt(SPEC_CONTENT, AGENTS_CONTENT, contracts, "")
    assert HOL_TITLE not in prompt
    assert HOL_BODY  not in prompt
    assert SPEC_CONTENT in prompt
```
