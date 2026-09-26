---
id: CON-0103
title: "LLM-Pool-Konfiguration – Provider-Einrichtung und Verbindungstest"
type: behavior
format: gherkin
spec: SPEC-0027
version: 0.1.0
status: deprecated
artifact: "contracts/behavior/llm-pool-configuration.feature"
tests:
- TST-0122
deprecated_reason: "LLM-Pool-Schritt des Wizards mit SPEC-0058 entfernt; Modelle stehen in llm.roles"
---

# Contract: LLM-Pool-Konfiguration – Provider-Einrichtung und Verbindungstest

> **Spec:** SPEC-0027 · **Typ:** Verhalten (Gherkin) · **Status:** draft

## Zweck

Definiert wie LLM-Provider konfiguriert, getestet und priorisiert werden:
mehrere Provider-Einträge, Strategie-Auswahl, `sdd config test-llm`-Ping,
und die Sicherheitsregel dass API-Keys nie direkt in `config.yaml` stehen (FR-05, FR-06, FR-07, FR-12).

## Garantien

- Beliebig viele LLM-Provider können im Pool hinterlegt werden (Anthropic, Ollama, OpenAI-compat, HuggingFace)
- Jeder Provider-Eintrag enthält: `id`, `type` (local|remote), `model`, `cost_tier`, `max_context_tokens`, sowie für remote `api_key_env`
- `sdd config test-llm [--id <id>]` sendet einen Ping-Prompt und meldet Erreichbarkeit + Latenz in ms
- Die Auswahlstrategie ist konfigurierbar: `cost_first`, `quality_first`, `local_first`
- API-Keys werden niemals direkt in `config.yaml` geschrieben — nur Env-Var-Namen

## Invarianten

- **INV-01:** Jede Provider-ID im Pool ist eindeutig; doppelte IDs werden mit Fehler abgelehnt.
- **INV-02:** Ein Remote-Provider ohne `api_key_env` wird als ungültig markiert (Validation-Fehler).
- **INV-03:** `test-llm` gibt Exit-Code 1 zurück wenn der Provider nicht erreichbar ist.
- **INV-04:** `api_key_env` muss einen Env-Var-Namen enthalten (kein direkter Schlüsselwert).

## Szenarien (Gherkin)

```gherkin
Feature: LLM-Pool-Konfiguration und Provider-Test

  Scenario: Mehrere Provider eintragen
    Given ein leerer LLM-Pool
    When der Nutzer Ollama (local) und Claude Sonnet (remote) über den Wizard einträgt
    Then enthält "config.yaml" zwei Provider-Einträge unter "llm_pool.providers"
    And jeder Eintrag hat die Pflichtfelder: id, type, model, cost_tier, max_context_tokens

  Scenario: Remote-Provider mit Env-Var für API-Key
    Given der Nutzer konfiguriert "claude-sonnet" als remote-Provider
    When er den API-Key-Env auf "ANTHROPIC_API_KEY" setzt
    Then steht in "config.yaml" "api_key_env: ANTHROPIC_API_KEY"
    And kein Klartext-API-Key ist in "config.yaml" enthalten (INV-04)

  Scenario: API-Key-Direkteingabe wird abgelehnt
    Given der Wizard fragt nach dem API-Key
    When der Nutzer einen Wert eingibt der mit "sk-" beginnt (direkter Key)
    Then zeigt der Wizard eine Sicherheitswarnung
    And fragt stattdessen nach dem Namen der Env-Variable

  Scenario: Provider-Verbindungstest erfolgreich
    Given "ollama-mistral" ist im Pool und Ollama läuft lokal
    When der Nutzer "sdd config test-llm --id ollama-mistral" ausführt
    Then antwortet der Befehl mit "OK" und einer Latenz in ms
    And Exit-Code ist 0

  Scenario: Provider nicht erreichbar
    Given "claude-sonnet" ist im Pool, aber ANTHROPIC_API_KEY ist nicht gesetzt
    When der Nutzer "sdd config test-llm --id claude-sonnet" ausführt
    Then antwortet der Befehl mit einer Fehlermeldung
    And Exit-Code ist 1 (INV-03)

  Scenario: Strategie local_first konfigurieren
    Given der Pool enthält "ollama-mistral" (local) und "claude-haiku" (remote, cheap)
    When der Nutzer die Strategie auf "local_first" setzt
    Then wird bei der Aufgabenverteilung "ollama-mistral" vor "claude-haiku" bevorzugt

  Scenario: Ungültige doppelte Provider-ID
    Given der Pool enthält bereits einen Provider mit id="ollama-mistral"
    When der Nutzer einen weiteren Provider mit id="ollama-mistral" einträgt
    Then schlägt die Validation fehl mit "Doppelte Provider-ID" (INV-01)
```

## Begriffe

| Begriff | Definition |
|---|---|
| cost_tier | Klassifizierung: cheap / standard / powerful |
| api_key_env | Name der Env-Variable die den API-Schlüssel enthält (kein Klartext) |
| local_first | Strategie: lokale Provider (Ollama) werden gegenüber remote bevorzugt |
| Ping-Prompt | Minimaler Test-Request um Erreichbarkeit + Latenz zu messen |
