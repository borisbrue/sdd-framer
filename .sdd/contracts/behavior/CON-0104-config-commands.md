---
id: CON-0104
title: "Config-Commands – sdd config set/get/show/validate"
type: behavior
format: gherkin
spec: SPEC-0027
version: 0.1.0
status: draft
artifact: "contracts/behavior/config-commands.feature"
tests:
- TST-0123
---

# Contract: Config-Commands – sdd config set/get/show/validate

> **Spec:** SPEC-0027 · **Typ:** Verhalten (Gherkin) · **Status:** draft

## Zweck

Definiert das Verhalten der nicht-interaktiven Config-Befehle:
`sdd config set`, `sdd config get`, `sdd config show` und `sdd config validate`
als diskrete CLI-Commands (Command Pattern) für manuelle und CI/CD-Nutzung (FR-02, FR-03, FR-04, FR-11).

## Garantien

- `sdd config set <key>=<value>` setzt einen einzelnen Wert via Dot-Notation und validiert sofort
- `sdd config get <key>` gibt den aktuellen Wert als Plain-Text zurück (maschinenlesbar)
- `sdd config show [--section <name>]` gibt die Konfiguration strukturiert und lesbar aus
- `sdd config validate` prüft Vollständigkeit, Konsistenz und Erreichbarkeit aller LLMs

## Invarianten

- **INV-01:** `set` schreibt atomar — entweder vollständig oder gar nicht; kein Teileintrag bei Fehler.
- **INV-02:** `get` auf einen nicht existierenden Key gibt Exit-Code 1 + leere Ausgabe.
- **INV-03:** `validate` gibt Exit-Code 0 bei valider Config, 1 mit einer Fehlerliste bei Problemen.
- **INV-04:** Array-Zugriff via `llm.pool[0].api_key_env` ist für `set` und `get` unterstützt.

## Szenarien (Gherkin)

```gherkin
Feature: Config-Commands set/get/show/validate

  Scenario: Einzelnen Wert setzen
    Given eine gültige "config.yaml"
    When der Nutzer "sdd config set docker.max_parallel_containers=4" ausführt
    Then enthält "config.yaml" den Wert 4 für "docker.max_parallel_containers"
    And "sdd config validate" meldet keine Fehler

  Scenario: Array-Element setzen via Index-Notation
    Given eine "config.yaml" mit einem LLM-Pool-Eintrag
    When der Nutzer "sdd config set llm.pool[0].api_key_env=ANTHROPIC_API_KEY" ausführt
    Then wird "api_key_env" des ersten Pool-Eintrags auf "ANTHROPIC_API_KEY" gesetzt (INV-04)

  Scenario: Einzelnen Wert lesen
    Given "config.yaml" enthält "docker.max_parallel_containers: 2"
    When der Nutzer "sdd config get docker.max_parallel_containers" ausführt
    Then ist die Ausgabe "2" (nur der Wert, kein Label)

  Scenario: Nicht-existierender Key beim get
    Given eine gültige "config.yaml"
    When der Nutzer "sdd config get llm.pool[5].model" ausführt
    Then ist die Ausgabe leer
    And Exit-Code ist 1 (INV-02)

  Scenario: Gesamte Konfiguration anzeigen
    Given eine gültige "config.yaml"
    When der Nutzer "sdd config show" ausführt
    Then zeigt die Ausgabe alle Sections strukturiert (Projekt, LLM, Docker, Evaluator)

  Scenario: Section-spezifische Anzeige
    Given eine gültige "config.yaml"
    When der Nutzer "sdd config show --section llm" ausführt
    Then zeigt die Ausgabe nur den LLM-Pool-Abschnitt

  Scenario: Vollständige Validierung
    Given eine "config.yaml" ohne api_key_env beim einzigen remote-Provider
    When der Nutzer "sdd config validate" ausführt
    Then ist Exit-Code 1
    And die Ausgabe enthält eine Fehlerliste mit dem fehlenden Pflichtfeld (INV-03)

  Scenario: Validierungsfehler beim set
    Given eine gültige "config.yaml"
    When der Nutzer "sdd config set docker.max_parallel_containers=-1" ausführt
    Then schlägt der Befehl fehl mit einer Validierungsfehlermeldung
    And "config.yaml" bleibt unverändert (INV-01)
```

## Begriffe

| Begriff | Definition |
|---|---|
| Dot-Notation | Schlüsselzugriff via Punkte, z.B. `docker.max_parallel_containers` |
| Array-Notation | Index-Zugriff via eckige Klammern, z.B. `llm.pool[0].model` |
| atomar | Schreiben als Ganzes — kein Zwischenzustand bei Fehler |
