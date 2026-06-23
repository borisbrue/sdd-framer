---
id: CON-0186
project: PRJ-0001
title: "Keyfreie Provider-Auflösung mit Fail-Loud"
type: behavior
format: gherkin
spec: SPEC-0050
version: 0.1.0
status: approved
artifact: "contracts/behavior/provider-resolution-keyless.feature"
tests: [TST-0212]
---

# Contract: Keyfreie Provider-Auflösung mit Fail-Loud

> **Spec:** SPEC-0050 · **Typ:** Verhalten (Gherkin) · **Status:** draft

## Zweck

Schreibt das Auflösungs- und Fehlerverhalten der Provider-Factory fest (FR-01, FR-02, FR-05):
keyfreier Default, expliziter anthropic-Opt-in, lautes Scheitern ohne stillen Fallback.

## Garantien

Die Szenarien im Artifact (`contracts/behavior/provider-resolution-keyless.feature`) sind
ausführbare Spezifikation und MÜSSEN durch automatisierte Tests abgedeckt sein.

## Invarianten

- **INV-01:** Ohne `llm`-Konfiguration liefert die Komponente `completion` einen `claude-cli`-Provider.
- **INV-02:** Ein explizit konfigurierter Provider (anthropic/openai-compat/huggingface) wird
  unverändert verwendet.
- **INV-03:** Ist der aufgelöste Provider nicht nutzbar, wird ein `RuntimeError` mit klarer Ursache
  geworfen; es erfolgt KEIN automatischer Wechsel auf einen anderen Provider.
- **INV-04:** Die Komponente `evaluator` bleibt keyfrei (claude-cli) – Regressionssicherung des
  Holdout-Gates.

## Geltungsbereich

- **In Scope:** `get_completion_provider`-Auflösung für `completion`/`evaluator`, Fehlerpfad.
- **Out of Scope:** Sichtbarkeit von LLM-Fehlern in pattern/solid (→ CON-0187); claude-cli-interne
  Mechanik.
