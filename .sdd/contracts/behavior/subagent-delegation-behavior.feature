Feature: Sub-Agenten-Delegation in sdd-implement (SPEC-0035)

  Scenario: Erfolgreiche Delegation mit Token-Tracking
    Given eine Spec SPEC-XXXX mit 4 Decompose-Tasks
    And der aktive Provider ist Claude
    When sdd-implement SPEC-XXXX ausgeführt wird
    Then werden 4 Sub-Agenten sequenziell gespawnt
    And jeder Sub-Agent startet mit leerem Kontext
    And token-history enthält 4 Einträge mit task_id für SPEC-XXXX

  Scenario: Sub-Agenten-Fehler mit Retry und Eskalation
    Given eine Spec SPEC-XXXX mit 3 Tasks
    And Task 2 schlägt fehl
    When sdd-implement SPEC-XXXX ausgeführt wird
    Then wird Task 2 einmal wiederholt
    And schlägt der Retry ebenfalls fehl
    Then hält der Orchestrator an und gibt einen Fehlerbericht aus
    And Task 3 wird nicht gestartet

  Scenario: Fallback bei Nicht-Claude-Provider
    Given eine Spec SPEC-XXXX
    And der aktive Provider ist nicht Claude
    When sdd-implement SPEC-XXXX ausgeführt wird
    Then läuft die Implementierung im Single-Context-Mode
    And der Output kennzeichnet Single-Context-Mode
