---
id: TST-0204
project: PRJ-0001
title: "sdd vision challenge – LLM- und Code-Challenge"
level: unit
spec: SPEC-0046
contract: CON-0178
status: draft
framework: pytest
artifact: "tests/unit/test_tst_0204.py"
tags:
  - vision
  - challenge
  - llm
  - async
  - spec-0008
  - spec-0016
---

# Test: sdd vision challenge – LLM- und Code-Challenge

> **Level:** unit · **Spec:** SPEC-0046 · **Contract:** CON-0178

## Was wird geprüft?

Prüft `LLMChallengeStrategy.challenge()` und `CodeChallengeStrategy.challenge()`:
SPEC-0008-Provider-Bindung, Ergebnis-Persistenz, Index-Validierung,
Überschreib-Verhalten, Fehlerfall keine Matches.

## Vorbedingungen

- `tool.sdd_cli.vision.challenge.LLMChallengeStrategy` existiert
- `tool.sdd_cli.vision.challenge.CodeChallengeStrategy` existiert
- LLMChallengeStrategy nutzt SPEC-0008 `get_ai_provider(config)`

## Ablauf

1. Strategien mit Mock-Provider / Mock-Dateisystem instanziieren
2. Ergebnis-Objekte prüfen
3. Persistenz in `.sdd/vision.md` prüfen

## Verknüpfung mit Contract (CON-0178)

- [x] INV-01: LLM-Aufruf via AIProvider-Interface (get_ai_provider), kein Direktzugriff
- [x] INV-02: LLM-Job async (Coroutine/awaitable)
- [x] INV-03: Code-Challenge synchron (kein await)
- [x] INV-04: Ungültiger Index → ValueError
- [x] INV-05: Ergebnis inline in vision.md als Blockquote gespeichert
- [x] INV-06: Bestehendes Ergebnis wird beim Neuaufruf überschrieben
- [x] INV-07: --llm / --code Flags isolieren die jeweilige Strategie
