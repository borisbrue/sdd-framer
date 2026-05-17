Feature: Test Run Results
  Als Entwickler möchte ich Tests einer Spec ausführen und die Ergebnisse einsehen,
  um die Qualität eines Features einschätzen zu können.

  Background:
    Given ein SDD-Projekt mit konfiguriertem pytest-Runner

  Scenario: Test-Run für eine Spec auslösen
    Given eine Spec "SPEC-0001" mit den Tests "TST-0001" und "TST-0003"
    And beide Test-Artefakte existieren als Python-Dateien
    When der Entwickler "sdd test-run SPEC-0001" ausführt
    Then werden beide Tests via pytest ausgeführt
    And das Ergebnis wird unter ".sdd/test-runs/SPEC-0001-*.json" gespeichert
    And der Exit-Code ist 0 wenn alle Tests grün sind

  Scenario: Ergebnisübersicht abrufen
    Given ein gespeicherter Test-Run für "SPEC-0001"
    When der Entwickler "sdd test-results SPEC-0001" ausführt
    Then wird eine Tabelle mit Pass/Fail/Skip-Anzahl angezeigt
    And die Contract-Coverage zeigt welche Contracts abgedeckt sind

  Scenario: Fehlgeschlagener Test im Report
    Given ein Test-Run bei dem ein Test fehlschlug
    When der Entwickler "sdd test-results" für die Spec aufruft
    Then wird der fehlgeschlagene Test als "failed" markiert
    And die Fehlermeldung wird unterhalb der Tabelle ausgegeben
    And der Exit-Code ist 1

  Scenario: Spec ohne verknüpfte Tests
    Given eine Spec mit leerem "tests:"-Frontmatter
    When der Entwickler "sdd test-run" für diese Spec aufruft
    Then wird die Warnung "Keine Tests verknüpft" angezeigt
    And der Exit-Code ist 2

  Scenario: Test-Artefakt ist Platzhalter
    Given ein TST-Dokument mit Platzhalter-Artefakt "tests/<level>/<name>.test.<ext>"
    When der Test-Run ausgeführt wird
    Then wird der Test als "missing" markiert
    And kein Fehler wird geworfen

  Scenario: Nicht-pytest-Artefakt wird übersprungen
    Given ein TST-Dokument mit Artefakt "tests/acceptance/login.feature"
    When der Test-Run ausgeführt wird
    Then wird der Test als "skipped" markiert mit Hinweis "runner: unsupported"
    And kein Fehler wird geworfen
