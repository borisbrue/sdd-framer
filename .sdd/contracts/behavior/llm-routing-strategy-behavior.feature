Feature: LlmRoutingStrategy – Routing-Entscheidung (SPEC-0036)

  Background:
    Given ContextSizeRoutingStrategy ist instanziiert
    And context_window ist 32768
    And context_reserve_tokens ist 4096

  Scenario: Kontext passt – Task wird lokal geroutet
    Given local_agent.enabled ist true
    And der Task-Kontext umfasst 20000 Tokens
    When route(task) aufgerufen wird
    Then gibt route "local" zurück

  Scenario: Kontext zu groß – Task wird in die Cloud geroutet
    Given local_agent.enabled ist true
    And der Task-Kontext umfasst 30000 Tokens
    When route(task) aufgerufen wird
    Then gibt route "cloud" zurück

  Scenario: Exakt an der Grenze – Task wird lokal geroutet
    Given local_agent.enabled ist true
    And der Task-Kontext umfasst 28672 Tokens
    When route(task) aufgerufen wird
    Then gibt route "local" zurück

  Scenario: local_agent deaktiviert – immer Cloud
    Given local_agent.enabled ist false
    And der Task-Kontext umfasst 1000 Tokens
    When route(task) aufgerufen wird
    Then gibt route "cloud" zurück

  Scenario: Token-Zählung erfolgt ohne Netzwerkaufruf
    Given local_agent.enabled ist true
    And kein Netzwerkzugang ist verfügbar
    And der Task-Kontext umfasst 10000 Tokens
    When route(task) aufgerufen wird
    Then wirft route() keine Netzwerk-Exception
    And gibt route "local" zurück
