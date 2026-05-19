Feature: Task-Lifecycle – Zustandsübergänge der Distribution Engine
  # CON-0095 | SPEC-0026

  Scenario: Erfolgreicher Durchlauf pending → committed
    Given ein Task T1 mit status="pending"
    When T1 einem LLM "llm-1" zugewiesen wird
    Then T1.status == "assigned"
    When T1 in Container "c1" gestartet wird
    Then T1.status == "running"
    When T1 zur Review eingereicht wird
    Then T1.status == "review"
    When Review bestanden
    And Commit "abc123" erzeugt
    Then T1.status == "committed"
    And T1.commit_hash == "abc123"

  Scenario: Fehlgeschlagene Review löst Retry aus
    Given ein Task T1 mit status="review"
    When Review fehlschlägt mit "TypeError"
    Then T1.status == "retrying"
    And T1.retry_count == 1
    And T1.error_context enthält "TypeError"

  Scenario: Maximale Retries erreicht – Task wird blocked
    Given ein Task T1 mit retry_count=3
    And T1 mit status="review"
    When Review erneut fehlschlägt
    Then T1.status == "blocked"
    And T1.retry_count == 3 (überschreitet nie MAX_RETRIES)

  Scenario: Ungültiger Übergang pending → committed
    Given ein Task T1 mit status="pending"
    When direkt commit("abc") aufgerufen wird
    Then wird InvalidTransitionError geworfen
