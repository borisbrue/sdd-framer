Feature: Keyfreie Provider-Auflösung mit Fail-Loud
  Die Provider-Factory wählt standardmäßig den keyfreien claude-cli-Provider und scheitert
  laut, statt still auf einen anderen Provider zurückzufallen. (SPEC-0050)

  Scenario: completion-Default ist claude-cli ohne Konfiguration
    Given eine config ohne jeglichen "llm"-Block
    When get_completion_provider(config, "completion") aufgerufen wird
    Then wird ein claude-cli-Provider zurückgegeben
    And es wird kein ANTHROPIC_API_KEY benötigt

  Scenario: Explizit konfigurierter anthropic-Provider bleibt nutzbar
    Given config mit llm.completion.provider = "anthropic" und gesetztem api_key
    When get_completion_provider(config, "completion") aufgerufen wird
    Then wird ein anthropic-Provider zurückgegeben

  Scenario: Nicht nutzbarer Provider scheitert laut ohne Fallback
    Given config mit llm.completion.provider = "anthropic" ohne api_key
    When get_completion_provider(config, "completion") aufgerufen und genutzt wird
    Then wird ein RuntimeError mit klarer Ursache geworfen
    And es erfolgt kein automatischer Wechsel auf claude-cli oder einen anderen Provider

  Scenario: Holdout-Gate bleibt keyfrei (Regressionssicherung)
    Given config mit llm.evaluator.provider = "claude-cli"
    When get_completion_provider(config, "evaluator") aufgerufen wird
    Then wird ein claude-cli-Provider zurückgegeben

  # FR-06: das Blueprint darf den keyfreien Builtin nicht wieder ueberschreiben.
  # Die beiden Ebenen arbeiteten vorher gegeneinander — Builtin keyfrei, Blueprint
  # auf anthropic —, sodass jedes neue Projekt doch einen Key verlangte.
  Scenario: Ein per sdd init erzeugtes Projekt startet keyfrei
    Given die Blueprint-config.yaml wird in ein neues Projekt kopiert
    When der llm-Block dieses Projekts ausgewertet wird
    Then ist fuer keine Komponente der Provider "anthropic" gesetzt
    And das Projekt ist ohne ANTHROPIC_API_KEY arbeitsfaehig

  # FR-07: FR-01 deckte nur `completion` ab. evaluator/ai_routes und der Fallback
  # fuer Komponenten ohne Builtin-Eintrag zeigten weiter auf anthropic — US-01 war
  # damit nicht erfuellt, obwohl FR-01 als erfuellt galt.
  Scenario Outline: Jede Komponente loest ohne Konfiguration keyfrei auf
    Given config ohne llm-Sektion
    When get_completion_provider(config, "<komponente>") aufgerufen wird
    Then wird ein claude-cli-Provider zurueckgegeben

    Examples:
      | komponente |
      | evaluator  |
      | ai_routes  |
      | local_llm  |
