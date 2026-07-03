Feature: sdd config validate CLI
  Als SDD-Nutzer
  möchte ich `sdd config validate` als eigenständigen Subcommand aufrufen können
  damit ich die config.yaml unabhängig vom normalen sdd-validate-Flow prüfen kann

  # FR-06: CLI-Integration
  Scenario: Valide Config erzeugt Exit-Code 0
    Given eine valide config.yaml mit gesetzten Feldern version, project.name, project.description
    When ich "sdd config validate" ausführe
    Then ist der Exit-Code 0
    And stdout enthält den Text "Config valide" oder "0 Fehler"

  Scenario: Config mit nur Warnings erzeugt Exit-Code 0
    Given eine config.yaml mit llm.completion.provider "anthropic"
    And kein api_key und kein ANTHROPIC_API_KEY ist gesetzt
    When ich "sdd config validate" ausführe
    Then ist der Exit-Code 0
    And stdout enthält das Wort "warning" oder "Warnung"

  Scenario: Fehlerhafte Config erzeugt Exit-Code 1
    Given eine config.yaml ohne das Feld "project.name"
    When ich "sdd config validate" ausführe
    Then ist der Exit-Code 1
    And stdout enthält den Feldpfad "project.name"

  Scenario: sdd validate bleibt unverändert
    Given eine valide config.yaml
    When ich "sdd validate" ausführe
    Then wird kein config.yaml-Feld geprüft
    And der Exit-Code entspricht dem Ergebnis der Struktur-Validierung (unverändert)

  # FR-07: JSON-Output
  Scenario: --json liefert valides JSON-Array bei Fehlern
    Given eine config.yaml mit llm.completion.provider "ungueltig"
    When ich "sdd config validate --json" ausführe
    Then ist stdout ein valides JSON-Array
    And jedes Element hat genau die Schlüssel "level", "path", "message"
    And mindestens ein Element hat "level": "error"
    And ist der Exit-Code 1

  Scenario: --json liefert leeres Array bei valider Config
    Given eine valide config.yaml
    When ich "sdd config validate --json" ausführe
    Then ist stdout exakt das JSON-Array "[]"
    And ist der Exit-Code 0

  Scenario: --json liefert Warning-Einträge bei anthropic ohne key
    Given eine config.yaml mit llm.completion.provider "anthropic" ohne api_key
    When ich "sdd config validate --json" ausführe
    Then ist stdout ein valides JSON-Array mit mindestens einem Element
    And das Element hat "level": "warning"
    And ist der Exit-Code 0

  Scenario: --json unterdrückt Rich-Markup in stdout
    Given eine config.yaml
    When ich "sdd config validate --json" ausführe
    Then enthält stdout keine ANSI-Escape-Sequenzen

  # Edge Cases
  Scenario: Fehlende config.yaml erzeugt Exit-Code 1 mit klarer Meldung
    Given kein Projektverzeichnis mit config.yaml
    When ich "sdd config validate" ausführe
    Then ist der Exit-Code 1
    And stdout enthält "config.yaml" und "nicht gefunden"

  Scenario: Syntaktisch ungültiges YAML erzeugt Exit-Code 1
    Given eine config.yaml mit dem Inhalt "key: [ungültig"
    When ich "sdd config validate" ausführe
    Then ist der Exit-Code 1
    And stdout enthält "YAML" oder "Parse"
