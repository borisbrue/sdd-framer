Feature: SOLID Analyzer Behavior

  Background:
    Given der SolidAnalyzer ist mit allen 5 Checkern (S, O, L, I, D) konfiguriert
    And solid_gate.enabled ist true

  Scenario: Konformes Artefakt erhält Score 'compliant'
    Given ein SPEC-Artefakt ohne erkennbare SOLID-Violations
    When der SolidAnalyzer das Artefakt analysiert
    Then ist overall_solid_score "compliant"
    And die findings-Liste ist leer oder enthält nur severity "info"

  Scenario: SRP-Violation wird als 'violation' gemeldet
    Given ein SPEC-Artefakt, das zwei unabhängige fachliche Domänen beschreibt
    When der SrpChecker das Artefakt analysiert
    Then enthält findings mindestens ein Eintrag mit principle "S" und severity "violation"
    And der Eintrag enthält ein nicht-leeres "location"-Feld
    And der Eintrag enthält ein nicht-leeres "suggestion"-Feld
    And overall_solid_score ist "violation"

  Scenario: OCP-Warnung bei fehlendem Erweiterungspunkt
    Given ein Contract-Artefakt ohne beschriebene Erweiterungsschnittstellen
    When der OcpChecker das Artefakt analysiert
    Then enthält findings mindestens ein Eintrag mit principle "O" und severity "warn" oder "violation"

  Scenario: NullSolidChecker liefert immer leeres Ergebnis
    Given solid_gate.enabled ist false
    And der SolidAnalyzer verwendet NullSolidChecker für alle Prinzipien
    When der SolidAnalyzer ein beliebiges Artefakt analysiert
    Then ist die findings-Liste leer
    And overall_solid_score ist "compliant"

  Scenario: Checker-Fehler unterbricht Kette nicht
    Given der IspChecker wirft eine RuntimeError-Exception
    When der SolidAnalyzer das Artefakt analysiert
    Then werden die verbleibenden Checker (D) trotzdem ausgeführt
    And findings enthält einen Eintrag mit principle "I", severity "info", description enthält "Checker-Fehler"

  Scenario: Score 'violation' wenn mindestens ein violation-Finding vorhanden
    Given findings enthält [severity "warn", severity "violation", severity "info"]
    When overall_solid_score berechnet wird
    Then ist overall_solid_score "violation"

  Scenario: Score 'warn' wenn nur warn-Findings, kein violation
    Given findings enthält [severity "warn", severity "info"]
    When overall_solid_score berechnet wird
    Then ist overall_solid_score "warn"
