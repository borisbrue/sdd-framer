---
id: CON-0069
title: "dev-stack-lifecycle"
type: behavior
format: gherkin
spec: SPEC-0022
version: 0.1.0
status: deprecated
artifact: "contracts/behavior/dev-stack-lifecycle.feature"
tests: [TST-0079]
deprecated_reason: "sdd dev build/push/up/down gibt es seit SPEC-0044 nicht mehr (#128). Das Image baut sdd start bei Bedarf, den Compose-Stack startet sdd start über docker.compose_file. Für push und down gibt es keinen Ersatz. Die Runtime-Abstraktion (Docker/Podman, G-02/G-07/INV-01) gilt weiter; TST-0079 prüft sie."
---

# Contract: dev-stack-lifecycle

> **Spec:** SPEC-0022 · **Typ:** Verhalten (Gherkin) · **Status:** draft

## Zweck

Beschreibt das beobachtbare Verhalten von `sdd dev build`, `sdd dev push`,
`sdd dev up` und `sdd dev down` inkl. Runtime-Auswahl (Docker/Podman).

## Garantien

- **G-01:** `sdd dev build` baut das Image aus `docker.dockerfile` mit dem Tag
  `docker.image`. Der Befehl delegiert an `docker.runtime` (docker|podman).
- **G-02:** Alle `sdd dev`-Befehle (SPEC-0021 + SPEC-0022) verwenden dieselbe
  `ContainerRuntime`-Instanz — kein direkter `docker`-Aufruf im Code.
- **G-03:** `sdd dev push` schiebt `docker.image` in `docker.registry.url`.
  Wenn `registry.url` leer ist: Fehlermeldung + Exit != 0.
- **G-04:** Wenn `docker.compose_file` konfiguriert ist, delegiert `sdd dev start`
  (SPEC-0021) intern an `sdd dev up`. Ohne `compose_file`: bisheriges Verhalten.
- **G-05:** `sdd dev up SPEC-XXXX` startet den Compose-Stack. Container-Name-
  Konvention aus SPEC-0021 bleibt erhalten.
- **G-06:** `sdd dev down SPEC-XXXX` stoppt den gesamten Compose-Stack.
- **G-07:** Runtime-Umschaltung von `docker` auf `podman` erfordert nur eine
  Konfigurationsänderung in `.sdd/config.yaml` — kein Code-Change.

## Invarianten

- **INV-01:** `docker.runtime` akzeptiert nur `docker` oder `podman` — andere
  Werte führen zu einer klaren Fehlermeldung beim Start.
- **INV-02:** `sdd dev build` schlägt fehl wenn `docker.dockerfile` nicht existiert.
- **INV-03:** Wenn `sdd dev up` aufgerufen wird ohne `compose_file`, wird
  ein klarer Fehler ausgegeben (nicht `sdd dev start` aufrufen).

## Szenarien

```gherkin
Feature: Dev-Stack Lifecycle (build/push/up/down)

  Background:
    Given ein SDD-Projekt mit .sdd/config.yaml
    And docker.runtime ist "docker"
    And docker.image ist "sdd-dev:latest"

  Scenario: sdd dev build – Image bauen
    Given docker.dockerfile ist ".sdd/Dockerfile" und existiert
    When der Nutzer "sdd dev build" ausführt
    Then wird "docker build -t sdd-dev:latest -f .sdd/Dockerfile ." ausgeführt
    And der Exit-Code ist 0

  Scenario: sdd dev build – mit Podman
    Given docker.runtime ist "podman"
    And docker.dockerfile existiert
    When der Nutzer "sdd dev build" ausführt
    Then wird "podman build -t sdd-dev:latest -f .sdd/Dockerfile ." ausgeführt
    And der Exit-Code ist 0

  Scenario: sdd dev build – Dockerfile fehlt
    Given docker.dockerfile existiert nicht
    When der Nutzer "sdd dev build" ausführt
    Then erscheint Fehler: "Dockerfile nicht gefunden: .sdd/Dockerfile"
    And der Exit-Code ist ungleich 0

  Scenario: sdd dev push – Image in Registry schieben
    Given docker.registry.url ist "registry.example.com/sdd"
    When der Nutzer "sdd dev push" ausführt
    Then wird "docker push registry.example.com/sdd/sdd-dev:latest" ausgeführt
    And der Exit-Code ist 0

  Scenario: sdd dev push – keine Registry konfiguriert
    Given docker.registry.url ist leer
    When der Nutzer "sdd dev push" ausführt
    Then erscheint Fehler: "Keine Registry konfiguriert (docker.registry.url)"
    And der Exit-Code ist ungleich 0

  Scenario: sdd dev up – Compose-Stack starten
    Given docker.compose_file ist ".sdd/docker-compose.yml" und existiert
    When der Nutzer "sdd dev up SPEC-0022" ausführt
    Then wird "docker compose -f .sdd/docker-compose.yml up -d" ausgeführt
    And LogStreamer wird für SPEC-0022 gestartet (wenn log_stream.enabled)
    And der Exit-Code ist 0

  Scenario: sdd dev down – Compose-Stack stoppen
    Given Compose-Stack für SPEC-0022 läuft
    When der Nutzer "sdd dev down SPEC-0022" ausführt
    Then wird "docker compose -f .sdd/docker-compose.yml down" ausgeführt
    And LogStreamer für SPEC-0022 wird gestoppt
    And der Exit-Code ist 0

  Scenario: sdd dev start delegiert an up (compose_file konfiguriert)
    Given docker.compose_file ist konfiguriert
    When der Nutzer "sdd dev start SPEC-0022" ausführt
    Then wird intern "sdd dev up SPEC-0022" aufgerufen
    And kein direkter "docker run" wird ausgeführt

  Scenario: ungültige Runtime in config
    Given docker.runtime ist "nerdctl"
    When ein beliebiger "sdd dev"-Befehl ausgeführt wird
    Then erscheint Fehler: "Ungültige Runtime 'nerdctl'. Erlaubt: docker, podman"
    And der Exit-Code ist ungleich 0
```

## Begriffe

| Begriff | Definition |
|---|---|
| ContainerRuntime | Interface das docker/podman-CLI kapselt (Strategy Pattern) |
| Compose-Stack | Gruppe von Services definiert in `docker.compose_file` |
