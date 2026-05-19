Feature: /sdd-config Claude-Code-Skill

  Scenario: Skill liest und zeigt aktuelle Konfiguration
    Given eine gültige "config.yaml" mit einem LLM-Provider
    When der Nutzer "/sdd-config" aufruft
    Then zeigt der Skill eine strukturierte Übersicht der aktuellen Konfiguration
    And hebt fehlende oder problematische Felder hervor

  Scenario: Skill erkennt fehlenden api_key_env
    Given "config.yaml" enthält einen remote-Provider ohne "api_key_env"
    When der Nutzer "/sdd-config" aufruft
    Then meldet der Skill "Remote-Provider hat kein api_key_env gesetzt"
    And schlägt den Env-Var-Namen als Korrektur vor

  Scenario: Änderung mit Bestätigung schreiben
    Given der Skill hat eine Änderung vorgeschlagen
    When der Nutzer "ja" antwortet
    Then schreibt der Skill die Änderung in "config.yaml"
    And führt "sdd config validate" aus
    And zeigt das Validierungsergebnis

  Scenario: Änderung ohne Bestätigung wird nicht geschrieben
    Given der Skill hat eine Änderung vorgeschlagen
    When der Nutzer "nein" antwortet
    Then bleibt "config.yaml" unverändert

  Scenario: Skill bei fehlender config.yaml
    Given kein SDD-Projekt initialisiert
    When der Nutzer "/sdd-config" aufruft
    Then bricht der Skill ab mit "Kein SDD-Projekt gefunden. Führe 'sdd init' aus."

  Scenario: API-Key wird niemals vorgeschlagen
    Given der Skill schlägt Konfigurationsänderungen vor
    Then enthält kein Vorschlag einen Klartext-API-Key
    And alle Key-Referenzen sind Env-Var-Namen
