Feature: PR-Workflow – Branch, Commits, Tests, Merge und Spec-Abschluss
  # CON-0101 | SPEC-0026

  Scenario: Alle Tasks committed – vollständiger Happy Path
    Given Spec SPEC-0026 mit 8 Tasks, alle status="committed"
    When orchestrator.finalize(SPEC-0026) aufgerufen wird
    Then existiert Branch "spec/SPEC-0026" mit 8 Commits
    And ein PR "LLM Task Distribution Engine" wird gegen main erstellt
    And die Test-Suite läuft auf dem PR
    When Tests: passed
    Then wird der PR in main gemergt
    And SPEC-0026.status == "implemented"
    And alle Container des Specs sind entfernt

  Scenario: Teilweise blockierte Tasks – PR mit Warnung
    Given SPEC-0026 mit 6 committed + 2 blocked Tasks
    When orchestrator.finalize(SPEC-0026) aufgerufen wird
    Then wird ein PR erstellt
    And der PR-Body listet die 2 blockierten Tasks
    And Entwickler muss manuell entscheiden (kein Auto-Merge)

  Scenario: Nur blockierte Tasks – kein PR
    Given SPEC-0026 mit 0 committed + 5 blocked Tasks
    When orchestrator.finalize(SPEC-0026) aufgerufen wird
    Then wird kein PR erstellt (INV-04)
    And Entwickler erhält Fehlermeldung mit allen blockierten Tasks

  Scenario: Tests schlagen fehl – kein Merge
    Given ein PR für SPEC-0026
    When Test-Suite fehlschlägt
    Then wird der PR nicht gemergt (INV-02)
    And SPEC-0026.status bleibt auf "in-progress"

  Scenario: Spec-Status nach Merge
    Given PR für SPEC-0026 wurde erfolgreich gemergt
    When update_spec_status("SPEC-0026") aufgerufen wird
    Then enthält SPEC-0026-Frontmatter "status: implemented" (INV-03)

  Scenario: Branch-Name-Format
    Given eine neue Spec-Ausführung für SPEC-0026
    When ensure_branch("SPEC-0026") aufgerufen wird
    Then lautet der Branch-Name "spec/SPEC-0026" (INV-01)
