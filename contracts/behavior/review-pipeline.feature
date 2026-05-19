Feature: ReviewPipeline – Automatische Prüfung und Retry-Logik
  # CON-0100 | SPEC-0026

  Scenario: Alle Stufen bestehen – Task wird committed
    Given Task T1 mit einem vollständigen LLM-Ergebnis
    When review_pipeline.run(T1) aufgerufen wird
    And Syntax-Check: passed
    And Unit-Tests: passed
    And Claude-Review: passed
    Then T1.status == "committed"
    And T1.commit_hash ist gesetzt (INV-03)

  Scenario: Syntax-Check schlägt fehl – Retry
    Given Task T1 mit retry_count=0
    When Syntax-Check für T1 schlägt fehl mit "TypeError: line 42"
    Then T1.error_context == ["TypeError: line 42"]
    And T1.retry_count == 1
    And T1.status == "retrying"
    And Unit-Tests und Claude-Review werden nicht ausgeführt (INV-01)

  Scenario: Dritter Fehlversuch – Task wird blocked
    Given Task T1 mit retry_count=3
    When Review erneut fehlschlägt
    Then T1.status == "blocked"

  Scenario: Retry erhält vollen Fehlerkontext
    Given Task T1 mit error_context=["Fehler 1", "Fehler 2"] und retry_count=2
    When Review mit "Fehler 3" fehlschlägt
    Then T1.error_context enthält "Fehler 1", "Fehler 2", "Fehler 3" (INV-04)
    And T1.status == "blocked" (max retries erreicht)

  Scenario: Claude-Review schlägt fehl, Syntax und Tests OK
    Given Task T1 mit retry_count=1
    When Syntax: passed, Tests: passed, Claude-Review: failed("SOLID-Verletzung")
    Then T1.error_context enthält "SOLID-Verletzung"
    And T1.retry_count == 2
    And T1.status == "retrying"

  Scenario: error_context wächst monoton
    Given Task T1 mit leerem error_context
    When Review fehlschlägt mit "err1"
    Then T1.error_context == ["err1"] (INV-02: keine Einträge werden gelöscht)
