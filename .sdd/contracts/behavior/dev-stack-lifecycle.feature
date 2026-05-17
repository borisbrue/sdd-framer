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
