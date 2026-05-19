---
id: CON-0107
title: "/sdd-config Claude-Code-Skill – Geführte Konfiguration in Claude Code"
type: behavior
format: gherkin
spec: SPEC-0027
version: 0.1.0
status: draft
artifact: "contracts/behavior/sdd-config-skill.feature"
tests:
- TST-0126
---

# Contract: /sdd-config Claude-Code-Skill – Geführte Konfiguration in Claude Code

> **Spec:** SPEC-0027 · **Typ:** Verhalten (Gherkin) · **Status:** draft

## Zweck

Definiert das Verhalten des `/sdd-config` Claude-Code-Skills: Lesen der aktuellen
`config.yaml`, Erkennen von Problemen, geführter Dialog mit Vorschlägen,
und atomares Schreiben nach Bestätigung (FR-10).

## Garantien

- Skill liest `config.yaml` beim Start vollständig ein
- Probleme werden erkannt und dem Nutzer klar beschrieben (fehlende Felder, ungültige Werte, nicht erreichbare Provider)
- Änderungen werden als Diff-Vorschlag präsentiert; Schreiben erst nach expliziter Nutzerbestätigung
- API-Keys werden niemals vorgeschlagen oder geschrieben — nur Env-Var-Namen
- Nach Schreiben führt der Skill `sdd config validate` aus und zeigt das Ergebnis

## Invarianten

- **INV-01:** Der Skill schreibt niemals ohne explizite Bestätigung ("ja" / "ok" / "speichern").
- **INV-02:** Der Skill liest niemals `.sdd/holdout/` — evaluator isolation gilt auch hier.
- **INV-03:** Bei fehlender `config.yaml` bricht der Skill mit einer verständlichen Meldung ab.

## Szenarien (Gherkin)

```gherkin
Feature: /sdd-config Claude-Code-Skill

  Scenario: Skill liest und zeigt aktuelle Konfiguration
    Given eine gültige "config.yaml" mit einem LLM-Provider
    When der Nutzer "/sdd-config" aufruft
    Then zeigt der Skill eine strukturierte Übersicht der aktuellen Konfiguration
    And hebt fehlende oder problematische Felder hervor

  Scenario: Skill erkennt fehlenden api_key_env
    Given "config.yaml" enthält einen remote-Provider ohne "api_key_env"
    When der Nutzer "/sdd-config" aufruft
    Then meldet der Skill "Remote-Provider 'X' hat kein api_key_env gesetzt"
    And schlägt den Env-Var-Namen als Korrektur vor

  Scenario: Änderung mit Bestätigung schreiben
    Given der Skill hat eine Änderung (neuer LLM-Provider) vorgeschlagen
    When der Nutzer "ja" antwortet
    Then schreibt der Skill die Änderung in "config.yaml"
    And führt "sdd config validate" aus
    And zeigt das Validierungsergebnis

  Scenario: Änderung ohne Bestätigung wird nicht geschrieben
    Given der Skill hat eine Änderung vorgeschlagen
    When der Nutzer "nein" antwortet
    Then bleibt "config.yaml" unverändert (INV-01)

  Scenario: Skill bei fehlender config.yaml
    Given kein SDD-Projekt initialisiert (keine "config.yaml")
    When der Nutzer "/sdd-config" aufruft
    Then bricht der Skill ab mit "Kein SDD-Projekt gefunden. Führe 'sdd init' aus." (INV-03)

  Scenario: API-Key wird niemals vorgeschlagen
    Given der Skill schlägt Konfigurationsänderungen vor
    Then enthält kein Vorschlag einen Klartext-API-Key
    And alle Key-Referenzen sind Env-Var-Namen (z.B. "ANTHROPIC_API_KEY")
```

## Begriffe

| Begriff | Definition |
|---|---|
| Diff-Vorschlag | Übersicht der geplanten Änderungen an `config.yaml` vor dem Schreiben |
| Env-Var-Name | Name einer Umgebungsvariablen (z.B. "ANTHROPIC_API_KEY"), nie der Schlüsselwert selbst |
| Bestätigung | Explizite Nutzerantwort ("ja", "ok", "speichern") vor dem Schreibvorgang |
