Feature: LLM-Pool-Konfiguration und Provider-Test

  Scenario: Mehrere Provider eintragen
    Given ein leerer LLM-Pool
    When der Nutzer Ollama (local) und Claude Sonnet (remote) über den Wizard einträgt
    Then enthält "config.yaml" zwei Provider-Einträge unter "llm_pool.providers"
    And jeder Eintrag hat die Pflichtfelder id, type, model, cost_tier, max_context_tokens

  Scenario: Remote-Provider mit Env-Var für API-Key
    Given der Nutzer konfiguriert "claude-sonnet" als remote-Provider
    When er den API-Key-Env auf "ANTHROPIC_API_KEY" setzt
    Then steht in "config.yaml" "api_key_env: ANTHROPIC_API_KEY"
    And kein Klartext-API-Key ist in "config.yaml" enthalten

  Scenario: API-Key-Direkteingabe wird abgelehnt
    Given der Wizard fragt nach dem API-Key
    When der Nutzer einen Wert eingibt der mit "sk-" beginnt
    Then zeigt der Wizard eine Sicherheitswarnung
    And fragt stattdessen nach dem Namen der Env-Variable

  Scenario: Provider-Verbindungstest erfolgreich
    Given "ollama-mistral" ist im Pool und Ollama läuft lokal
    When der Nutzer "sdd config test-llm --id ollama-mistral" ausführt
    Then antwortet der Befehl mit "OK" und einer Latenz in ms
    And Exit-Code ist 0

  Scenario: Provider nicht erreichbar
    Given "claude-sonnet" ist im Pool aber ANTHROPIC_API_KEY ist nicht gesetzt
    When der Nutzer "sdd config test-llm --id claude-sonnet" ausführt
    Then antwortet der Befehl mit einer Fehlermeldung
    And Exit-Code ist 1

  Scenario: Strategie local_first konfigurieren
    Given der Pool enthält "ollama-mistral" (local) und "claude-haiku" (remote, cheap)
    When der Nutzer die Strategie auf "local_first" setzt
    Then wird bei der Aufgabenverteilung "ollama-mistral" vor "claude-haiku" bevorzugt

  Scenario: Ungültige doppelte Provider-ID
    Given der Pool enthält bereits einen Provider mit id="ollama-mistral"
    When der Nutzer einen weiteren Provider mit id="ollama-mistral" einträgt
    Then schlägt die Validation fehl mit "Doppelte Provider-ID"
