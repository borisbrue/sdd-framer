Feature: Config-Validierungsregeln
  Als SDD-Nutzer
  möchte ich beim Start sofort Feedback über Fehler in der config.yaml erhalten
  damit ich sie beheben kann bevor ein Analyse-Lauf startet

  # FR-01: Pflichtfelder
  Scenario: Fehlende Pflichtfelder werden als error gemeldet
    Given eine config.yaml ohne das Feld "project.name"
    When der ConfigValidator ausgeführt wird
    Then enthält das Ergebnis einen Eintrag mit level "error"
    And der Feldpfad ist "project.name"
    And der Exit-Code ist 1

  Scenario: Fehlender version-Schlüssel wird als error gemeldet
    Given eine config.yaml ohne das Feld "version"
    When der ConfigValidator ausgeführt wird
    Then enthält das Ergebnis einen Eintrag mit level "error"
    And der Feldpfad ist "version"

  Scenario: Valide Pflichtfelder erzeugen keine Fehler
    Given eine config.yaml mit gesetzten Feldern "version", "project.name", "project.description"
    When der ConfigValidator ausgeführt wird
    Then enthält das Ergebnis keinen Eintrag mit level "error" für Pflichtfelder

  # FR-02: Provider-Enum
  Scenario: Ungültiger Provider-Name wird als error gemeldet
    Given eine config.yaml mit llm.completion.provider "foobar"
    When der ConfigValidator ausgeführt wird
    Then enthält das Ergebnis einen Eintrag mit level "error"
    And die Nachricht nennt die erlaubten Provider-Werte

  Scenario: Gültiger Provider-Name erzeugt keinen Fehler
    Given eine config.yaml mit llm.completion.provider "openai-compat"
    And llm.completion.base_url und model sind gesetzt
    When der ConfigValidator ausgeführt wird
    Then enthält das Ergebnis keinen Eintrag mit level "error" für den Provider-Enum-Check

  # FR-03: openai-compat-Konsistenz
  Scenario: openai-compat ohne base_url wird als error gemeldet
    Given eine config.yaml mit llm.completion.provider "openai-compat"
    And llm.completion.base_url ist nicht gesetzt
    When der ConfigValidator ausgeführt wird
    Then enthält das Ergebnis einen Eintrag mit level "error"
    And der Feldpfad ist "llm.completion.base_url"

  Scenario: openai-compat ohne model wird als error gemeldet
    Given eine config.yaml mit llm.completion.provider "openai-compat"
    And llm.completion.model ist nicht gesetzt
    When der ConfigValidator ausgeführt wird
    Then enthält das Ergebnis einen Eintrag mit level "error"
    And der Feldpfad ist "llm.completion.model"

  # FR-04: huggingface-Konsistenz
  Scenario: huggingface ohne hf_token (serverless) wird als error gemeldet
    Given eine config.yaml mit llm.completion.provider "huggingface"
    And hf_mode ist "serverless"
    And weder hf_token noch HF_TOKEN-Env-Var ist gesetzt
    When der ConfigValidator ausgeführt wird
    Then enthält das Ergebnis einen Eintrag mit level "error"

  # FR-05: anthropic-Konsistenz (Warning)
  Scenario: anthropic ohne api_key erzeugt nur eine Warnung
    Given eine config.yaml mit llm.completion.provider "anthropic"
    And weder api_key noch ANTHROPIC_API_KEY-Env-Var ist gesetzt
    When der ConfigValidator ausgeführt wird
    Then enthält das Ergebnis einen Eintrag mit level "warning"
    And enthält das Ergebnis keinen Eintrag mit level "error" für den anthropic-Key-Check
