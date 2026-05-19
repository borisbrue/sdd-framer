Feature: Container-Lifecycle – Erstellung, Task-Zuweisung und Cleanup
  # CON-0099 | SPEC-0026

  Scenario: Container mit einem Task erstellen und starten
    Given Git-HEAD ist commit "abc123"
    And ein Task T1 für SPEC-0026
    When container.create([T1]) aufgerufen wird
    Then existiert ein Container mit Name-Schema "sdd-spec-0026-<uuid>"
    And der Code-Stand im Container entspricht commit "abc123"

  Scenario: Mehrere Tasks in einem Container
    Given drei Tasks T1, T2, T3 mit complexity="low"
    When container.create([T1, T2, T3]) aufgerufen wird
    Then sind alle drei Tasks dem selben Container zugewiesen

  Scenario: Leere Task-Liste ist unzulässig
    Given eine leere Task-Liste []
    When container.create([]) aufgerufen wird
    Then wird AssertionError geworfen (INV-01)

  Scenario: Cleanup nach Abschluss
    Given Container C1 mit Task T1 (status: committed)
    When container.remove(C1) aufgerufen wird
    Then existiert kein Container mit ID C1 mehr (INV-04)

  Scenario: remove() ist idempotent
    Given Container C1 bereits entfernt
    When container.remove(C1) erneut aufgerufen wird
    Then kein Fehler wird geworfen

  Scenario: Task erhält container_id nach Zuweisung
    Given Task T1 mit status="assigned"
    When lc.start_running("sdd-spec-0026-x") aufgerufen wird
    Then T1.container_id == "sdd-spec-0026-x"
    And T1.status == "running"
