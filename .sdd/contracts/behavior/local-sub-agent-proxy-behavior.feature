Feature: LocalSubAgentProxy – Ausführung und Fehler-Eskalation (SPEC-0036)

  Scenario: Erfolgreiche lokale Ausführung setzt korrekte Env-Variablen
    Given LocalSubAgentProxy ist mit proxy_url "http://localhost:4000" konfiguriert
    And api_key ist "local-key"
    When execute(task) aufgerufen wird
    Then wird claude CLI als Subprocess mit ANTHROPIC_BASE_URL="http://localhost:4000" gestartet
    And ANTHROPIC_API_KEY="local-key" ist im Subprocess-Environment gesetzt
    And die Host-Prozess-Env-Variablen sind nach execute() unverändert

  Scenario: api_key erscheint nicht in Logs
    Given LocalSubAgentProxy ist mit api_key "secret-key" konfiguriert
    When execute(task) aufgerufen wird (erfolgreich oder fehlerhaft)
    Then enthält kein Log-Eintrag den String "secret-key"
    And enthält kein Subprocess-Argument den String "secret-key"

  Scenario: Lokaler Proxy-Fehler eskaliert sofort zu Cloud
    Given LocalSubAgentProxy.execute() wirft ConnectionError
    When DagScheduler execute(task) über LocalSubAgentProxy aufruft
    Then wird CloudSubAgentProxy.execute(task) aufgerufen
    And kein lokaler Retry findet statt

  Scenario: Proxy-Verbindungsfehler während Task eskaliert zu Cloud
    Given LocalSubAgentProxy.execute() startet erfolgreich
    And der Subprocess bricht mit Netzwerkfehler ab
    When DagScheduler den Fehler empfängt
    Then wird CloudSubAgentProxy.execute(task) aufgerufen

  Scenario: Cloud-Eskalation schlägt ebenfalls fehl – Orchestrator hält an
    Given LocalSubAgentProxy.execute() schlägt fehl
    And CloudSubAgentProxy.execute() schlägt nach 1 Retry ebenfalls fehl
    When DagScheduler den Fehler empfängt
    Then hält der DagScheduler an
    And gibt einen Fehlerbericht für den betroffenen Task aus
    And nachfolgende Tasks werden nicht gestartet

  Scenario: SubAgentProxy-Interface ist polymorph
    Given LocalSubAgentProxy und CloudSubAgentProxy implementieren SubAgentProxy-Protocol
    When DagScheduler eine SubAgentProxy-Instanz erhält
    Then kann DagScheduler execute() aufrufen ohne Typ-Check
