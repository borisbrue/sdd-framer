---
id: CON-0105
title: "Docker-Container-Konfiguration – Ressourcen, Parallelität und Cleanup via Wizard"
type: behavior
format: gherkin
spec: SPEC-0027
version: 0.1.0
status: draft
artifact: "contracts/behavior/docker-container-config.feature"
tests:
- TST-0124
---

# Contract: Docker-Container-Konfiguration – Ressourcen, Parallelität und Cleanup via Wizard

> **Spec:** SPEC-0027 · **Typ:** Verhalten (Gherkin) · **Status:** draft

## Zweck

Definiert wie Docker/Podman-Runtime, Ressourcenlimits, Parallelität und Cleanup-Verhalten
via `sdd config wizard --section docker` eingerichtet werden und welche Werte an
`docker run` weitergegeben werden (FR-13, FR-14, FR-15, FR-16).

## Garantien

- Wizard konfiguriert: `runtime` (docker|podman), `image`, `dockerfile`, `max_parallel_containers`, `resources.cpu_limit`, `resources.memory_limit`, `cleanup.on_success`, `cleanup.on_failure`, `registry.url`, `registry.auth_env`
- `max_parallel_containers` begrenzt gleichzeitig laufende Container bei `sdd distribute` und `sdd finalize`
- `cpu_limit` und `memory_limit` werden als Docker-Run-Flags übergeben (`--cpus`, `--memory`)
- `cleanup.on_success: true` entfernt Container nach erfolgreichem Test automatisch
- `cleanup.on_failure: false` bewahrt Container bei Fehler für Debugging
- `skip_if_unavailable: false` bricht bei fehlendem Docker ab; `true` erlaubt Fallback auf lokale Tests

## Invarianten

- **INV-01:** `max_parallel_containers` muss ≥ 1 sein; Eingabe < 1 wird abgelehnt.
- **INV-02:** `cpu_limit` muss ein positiver Float-Wert sein (z.B. `"1.0"`); `memory_limit` muss Docker-Notation folgen (z.B. `"1g"`, `"512m"`).
- **INV-03:** Wenn `registry.url` gesetzt ist, muss auch `registry.auth_env` gesetzt sein.
- **INV-04:** Defaults: `max_parallel_containers=2`, `cleanup.on_success=true`, `cleanup.on_failure=false`, `skip_if_unavailable=false`.

## Szenarien (Gherkin)

```gherkin
Feature: Docker-Container-Konfiguration

  Scenario: Wizard konfiguriert Docker-Abschnitt vollständig
    Given der Wizard befindet sich im Docker-Abschnitt
    When der Nutzer Runtime="docker", Image="sdd-dev:latest", max_parallel=2 eingibt
    Then enthält "config.yaml" alle Docker-Felder korrekt

  Scenario: Ressourcenlimits werden als Docker-Flags übergeben
    Given "config.yaml" enthält cpu_limit="1.0" und memory_limit="1g"
    When "sdd finalize" einen Container startet
    Then enthält der docker-run-Befehl "--cpus=1.0" und "--memory=1g"

  Scenario: Cleanup nach Erfolg
    Given cleanup.on_success=true in der Config
    When Container-Tests erfolgreich abschließen
    Then wird der Container automatisch entfernt (docker rm)

  Scenario: Container bleibt bei Fehler erhalten
    Given cleanup.on_failure=false in der Config
    When Container-Tests fehlschlagen
    Then bleibt der Container für Debugging-Zwecke erhalten

  Scenario: Parallelitäts-Limit wird durchgesetzt
    Given max_parallel_containers=2 in der Config
    When "sdd distribute" 5 Tasks gleichzeitig starten möchte
    Then laufen maximal 2 Container parallel; die anderen warten in der Queue

  Scenario: Ungültiger max_parallel_containers-Wert
    Given der Wizard fragt nach max_parallel_containers
    When der Nutzer "0" eingibt
    Then zeigt der Wizard eine Fehlermeldung "Muss mindestens 1 sein" (INV-01)

  Scenario: Registry mit Auth-Env
    Given der Nutzer setzt registry.url="registry.example.com"
    When registry.auth_env leer bleibt
    Then schlägt die Validation fehl mit "auth_env erforderlich wenn url gesetzt" (INV-03)

  Scenario: skip_if_unavailable Fallback
    Given skip_if_unavailable=true in der Config
    And Docker ist nicht verfügbar
    When "sdd finalize" aufgerufen wird
    Then werden Tests lokal ohne Container ausgeführt
    And eine Warnung wird ausgegeben
```

## Begriffe

| Begriff | Definition |
|---|---|
| max_parallel_containers | Maximale Anzahl gleichzeitig laufender Container |
| cpu_limit | Docker `--cpus`-Flag-Wert (Float, z.B. "1.0") |
| memory_limit | Docker `--memory`-Flag-Wert (z.B. "1g", "512m") |
| skip_if_unavailable | Erlaubt lokale Test-Ausführung wenn Docker fehlt |
