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
    Then wird der Container automatisch entfernt

  Scenario: Container bleibt bei Fehler erhalten
    Given cleanup.on_failure=false in der Config
    When Container-Tests fehlschlagen
    Then bleibt der Container für Debugging-Zwecke erhalten

  Scenario: Parallelitäts-Limit wird durchgesetzt
    Given max_parallel_containers=2 in der Config
    When "sdd distribute" 5 Tasks gleichzeitig starten möchte
    Then laufen maximal 2 Container parallel
    And die anderen warten in der Queue

  Scenario: Ungültiger max_parallel_containers-Wert
    Given der Wizard fragt nach max_parallel_containers
    When der Nutzer "0" eingibt
    Then zeigt der Wizard eine Fehlermeldung "Muss mindestens 1 sein"

  Scenario: Registry mit fehlendem Auth-Env
    Given der Nutzer setzt registry.url="registry.example.com"
    When registry.auth_env leer bleibt
    Then schlägt die Validation fehl mit "auth_env erforderlich wenn url gesetzt"

  Scenario: skip_if_unavailable Fallback auf lokale Tests
    Given skip_if_unavailable=true in der Config
    And Docker ist nicht verfügbar
    When "sdd finalize" aufgerufen wird
    Then werden Tests lokal ohne Container ausgeführt
    And eine Warnung wird ausgegeben
