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
