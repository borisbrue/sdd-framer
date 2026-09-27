Feature: Pipeline-Budget
  Als Nutzer der Pipeline
  möchte ich die Tokens eines Runs begrenzen
  um Kosten und Laufzeit im Griff zu behalten

  Scenario: Budget aus der Run-Option
    Given ein Run mit --max-tokens 100
    When die Rollen mehr als 100 Tokens verbrauchen
    Then hält der Run mit Grund budget und Exit 1
    And run.json enthält options.budget.max_tokens 100

  Scenario: Budget aus der Config
    Given pipeline.budget.max_tokens ist 100 in config.yaml
    When ein Run mehr als 100 Tokens verbraucht
    Then hält der Run mit Grund budget

  Scenario: Claude-Budget zählt nur Claude-Rollen
    Given supervisor ist mit claude-cli belegt und --max-claude-tokens ist 100
    When nur lokale Rollen mehr als 100 Tokens verbrauchen
    Then läuft der Run weiter

  Scenario: Kein Budget
    Given weder Option noch Config setzen ein Budget
    When ich "sdd pipeline run SPEC-0900" ausführe
    Then endet der Run ohne Halt wegen budget

  Scenario: Ungültiges Budget
    When ich "sdd pipeline run SPEC-0900 --max-tokens 0" ausführe
    Then ist der Exit-Code 2
