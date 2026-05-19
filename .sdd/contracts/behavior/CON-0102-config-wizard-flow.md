---
id: CON-0102
title: "Config-Wizard-Flow – Geführte Einrichtung via sdd config wizard"
type: behavior
format: gherkin
spec: SPEC-0027
version: 0.1.0
status: draft
artifact: "contracts/behavior/config-wizard-flow.feature"
tests:
- TST-0121
---

# Contract: Config-Wizard-Flow – Geführte Einrichtung via sdd config wizard

> **Spec:** SPEC-0027 · **Typ:** Verhalten (Gherkin) · **Status:** draft

## Zweck

Definiert das beobachtbare Verhalten des interaktiven `sdd config wizard`-Befehls:
Schritt-für-Schritt-Führung durch alle Konfigurationsabschnitte, Section-Routing,
automatischer Start nach `sdd init` und CI/CD-Modus ohne Prompts (FR-01, FR-08, FR-09).

## Garantien

- Der Wizard führt sequenziell durch: Projekt → LLM-Pool → Docker → Evaluator → Orchestrator → Validation
- Jeder Abschnitt ist einzeln erreichbar via `--section <name>`
- Nach `sdd init` startet der Wizard automatisch, wenn `project.description` den Platzhalter enthält
- Im `--non-interactive`-Modus werden alle Werte aus Flags/Env-Vars geladen, kein Prompt erscheint
- Am Ende wird `config.yaml` atomar geschrieben; kein Teilzustand bei Abbruch
- Der Wizard schreibt nie API-Keys direkt — nur Env-Var-Namen

## Invarianten

- **INV-01:** Wizard-Abbruch (Ctrl+C) vor dem finalen Schreiben lässt die bestehende `config.yaml` unverändert.
- **INV-02:** Jede Section-Antwort wird sofort validiert; bei ungültiger Eingabe folgt eine Fehlermeldung + Wiederholung.
- **INV-03:** Im `--non-interactive`-Modus produziert der Wizard Exit-Code 0 bei Erfolg, 1 bei Validierungsfehler.

## Szenarien (Gherkin)

```gherkin
Feature: Config-Wizard-Flow

  Scenario: Vollständiger Wizard-Durchlauf
    Given ein SDD-Projekt ohne vollständige Konfiguration
    When der Nutzer "sdd config wizard" ausführt
    Then werden alle Sections (Projekt, LLM, Docker, Evaluator, Orchestrator) nacheinander abgefragt
    And nach Bestätigung wird "config.yaml" vollständig geschrieben
    And "sdd validate" meldet keine Fehler

  Scenario: Section-spezifischer Wizard
    Given eine gültige "config.yaml" mit veralteten LLM-Einträgen
    When der Nutzer "sdd config wizard --section llm" ausführt
    Then wird nur der LLM-Pool-Abschnitt abgefragt
    And alle anderen Sections bleiben unverändert

  Scenario: Automatischer Wizard nach sdd init
    Given ein frisch initialisiertes Projekt
    And "project.description" enthält den Platzhalter "Beschreibe dein Projekt"
    When der Nutzer "sdd init" abgeschlossen hat
    Then startet der Wizard automatisch mit einer Hinweismeldung

  Scenario: CI/CD non-interaktiver Modus
    Given keine interaktive TTY-Verbindung
    When der Nutzer "sdd config set llm.pool[0].api_key_env=ANTHROPIC_API_KEY --non-interactive" ausführt
    Then wird der Wert gesetzt ohne Prompt
    And Exit-Code ist 0

  Scenario: Wizard-Abbruch lässt Config unverändert
    Given eine gültige "config.yaml"
    When der Nutzer den Wizard mit Ctrl+C abbricht (nach Section 1)
    Then ist "config.yaml" identisch zum Stand vor dem Wizard-Start (INV-01)

  Scenario: Ungültige Eingabe im Wizard
    Given der Wizard befindet sich im Docker-Abschnitt
    When der Nutzer einen negativen Wert für "max_parallel_containers" eingibt
    Then zeigt der Wizard eine Fehlermeldung
    And fragt den Wert erneut ab (INV-02)
```

## Begriffe

| Begriff | Definition |
|---|---|
| Section | Konfigurationsabschnitt (llm, docker, evaluator, orchestrator, project) |
| Platzhalter | Standard-Beschreibung aus `sdd init`-Template, signalisiert fehlende Konfiguration |
| non-interactive | Modus ohne TTY-Prompts, alle Werte kommen aus Flags oder Env-Vars |
