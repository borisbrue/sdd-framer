---
id: CON-0098
title: "LLM-Pool-Registry und Selector – Task-zu-LLM-Matching"
type: behavior
format: gherkin
spec: SPEC-0026
version: 0.1.0
status: draft
artifact: "contracts/behavior/llm-pool-registry.feature"
tests:
- TST-0117
---

# Contract: LLM-Pool-Registry und Selector – Task-zu-LLM-Matching

> **Spec:** SPEC-0026 · **Typ:** Verhalten (Gherkin) · **Status:** draft

## Zweck

Legt fest, wie verfügbare LLMs konfiguriert werden und wie der `LlmSelector`
anhand der Task-Klassifizierung das optimale LLM auswählt (FR-04/05).
Baut auf dem Provider-Abstraktionslayer aus SPEC-0008 auf.

## Garantien

- Die Registry liest LLM-Einträge aus `.sdd/config.yaml` (Abschnitt `llm_pool`).
- Jeder Eintrag hat: `id`, `type` (local|remote), `model`, `cost_tier` (cheap|standard|powerful), `max_context_tokens`.
- `LlmSelector` wählt nach Strategie: low/S → `cheap`, medium/M → `standard`, high/L → `powerful`.
- Ist das bevorzugte Tier nicht verfügbar, fällt der Selector auf das nächste verfügbare Tier zurück.
- Ist kein LLM verfügbar, bricht die Verteilung mit einem Fehler ab.

## Invarianten

- **INV-01:** Jede LLM-ID in der Registry ist einmalig.
- **INV-02:** Ein Task wird nie an ein LLM zugewiesen, dessen `max_context_tokens` kleiner als `estimated_tokens` des Tasks ist.
- **INV-03:** Lokale LLMs werden bei gleichem Tier gegenüber remote bevorzugt (Kostenminimierung).

## Szenarien (Gherkin)

```gherkin
Feature: LLM-Pool-Registry und Selector

  Scenario: Low-Complexity Task geht an lokales LLM
    Given die Registry enthält "ollama/mistral" (local, cheap) und "claude-haiku" (remote, cheap)
    And ein Task mit complexity="low", context_size="S"
    When LlmSelector.select(task) aufgerufen wird
    Then wird "ollama/mistral" zurückgegeben (INV-03: lokal bevorzugt)

  Scenario: High-Complexity Task geht an powerful LLM
    Given die Registry enthält "ollama/mistral" (cheap) und "claude-opus" (powerful)
    And ein Task mit complexity="high", context_size="L"
    When LlmSelector.select(task) aufgerufen wird
    Then wird "claude-opus" zurückgegeben

  Scenario: Fallback wenn bevorzugtes Tier fehlt
    Given die Registry enthält nur "claude-haiku" (cheap)
    And ein Task mit complexity="high", context_size="L"
    When LlmSelector.select(task) aufgerufen wird
    Then wird "claude-haiku" als Fallback zurückgegeben

  Scenario: Kontext-Limit-Verletzung
    Given "ollama/mistral" hat max_context_tokens=4096
    And ein Task mit estimated_tokens=8000
    When LlmSelector.select(task) aufgerufen wird
    Then wird "ollama/mistral" nicht ausgewählt (INV-02)

  Scenario: Leere Registry
    Given die Registry ist leer
    When LlmSelector.select(task) aufgerufen wird
    Then wird LlmUnavailableError geworfen
```

## Begriffe

| Begriff | Definition |
|---|---|
| cost_tier | Klassifizierung cheap / standard / powerful |
| Fallback | Nächstes verfügbares Tier wenn bevorzugtes fehlt |
