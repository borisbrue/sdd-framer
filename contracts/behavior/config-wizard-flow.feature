Feature: Config-Wizard-Flow

  Scenario: Vollständiger Wizard-Durchlauf
    Given ein SDD-Projekt ohne vollständige Konfiguration
    When der Nutzer "sdd config wizard" ausführt
    Then werden alle Sections (Projekt, LLM, Docker, Evaluator, Orchestrator) nacheinander abgefragt
    And nach Bestätigung wird "config.yaml" vollständig geschrieben
    And "sdd validate" meldet keine Fehler

  Scenario: Section-spezifischer Wizard
    Given eine gültige "config.yaml" mit veralteten LLM-Einträgen
    When der Nutzer "sdd config wizard --section llm" ausführt
    Then wird nur der LLM-Pool-Abschnitt abgefragt
    And alle anderen Sections bleiben unverändert

  Scenario: Automatischer Wizard nach sdd init
    Given ein frisch initialisiertes Projekt
    And "project.description" enthält den Platzhalter "Beschreibe dein Projekt"
    When der Nutzer "sdd init" abgeschlossen hat
    Then startet der Wizard automatisch mit einer Hinweismeldung

  Scenario: CI/CD non-interaktiver Modus
    Given keine interaktive TTY-Verbindung
    When der Nutzer "sdd config set llm.pool[0].api_key_env=ANTHROPIC_API_KEY --non-interactive" ausführt
    Then wird der Wert gesetzt ohne Prompt
    And Exit-Code ist 0

  Scenario: Wizard-Abbruch lässt Config unverändert
    Given eine gültige "config.yaml"
    When der Nutzer den Wizard mit Ctrl+C abbricht nach Section 1
    Then ist "config.yaml" identisch zum Stand vor dem Wizard-Start

  Scenario: Ungültige Eingabe im Wizard
    Given der Wizard befindet sich im Docker-Abschnitt
    When der Nutzer einen negativen Wert für "max_parallel_containers" eingibt
    Then zeigt der Wizard eine Fehlermeldung
    And fragt den Wert erneut ab
