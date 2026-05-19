Feature: Config-Commands set/get/show/validate

  Scenario: Einzelnen Wert setzen
    Given eine gültige "config.yaml"
    When der Nutzer "sdd config set docker.max_parallel_containers=4" ausführt
    Then enthält "config.yaml" den Wert 4 für "docker.max_parallel_containers"
    And "sdd config validate" meldet keine Fehler

  Scenario: Array-Element setzen via Index-Notation
    Given eine "config.yaml" mit einem LLM-Pool-Eintrag
    When der Nutzer "sdd config set llm.pool[0].api_key_env=ANTHROPIC_API_KEY" ausführt
    Then wird "api_key_env" des ersten Pool-Eintrags auf "ANTHROPIC_API_KEY" gesetzt

  Scenario: Einzelnen Wert lesen
    Given "config.yaml" enthält "docker.max_parallel_containers: 2"
    When der Nutzer "sdd config get docker.max_parallel_containers" ausführt
    Then ist die Ausgabe "2"

  Scenario: Nicht-existierender Key beim get
    Given eine gültige "config.yaml"
    When der Nutzer "sdd config get llm.pool[5].model" ausführt
    Then ist die Ausgabe leer
    And Exit-Code ist 1

  Scenario: Gesamte Konfiguration anzeigen
    Given eine gültige "config.yaml"
    When der Nutzer "sdd config show" ausführt
    Then zeigt die Ausgabe alle Sections strukturiert

  Scenario: Section-spezifische Anzeige
    Given eine gültige "config.yaml"
    When der Nutzer "sdd config show --section llm" ausführt
    Then zeigt die Ausgabe nur den LLM-Pool-Abschnitt

  Scenario: Vollständige Validierung mit Fehler
    Given eine "config.yaml" ohne api_key_env beim einzigen remote-Provider
    When der Nutzer "sdd config validate" ausführt
    Then ist Exit-Code 1
    And die Ausgabe enthält eine Fehlerliste mit dem fehlenden Pflichtfeld

  Scenario: Validierungsfehler beim set verhindert Schreiben
    Given eine gültige "config.yaml"
    When der Nutzer "sdd config set docker.max_parallel_containers=-1" ausführt
    Then schlägt der Befehl fehl mit einer Validierungsfehlermeldung
    And "config.yaml" bleibt unverändert
