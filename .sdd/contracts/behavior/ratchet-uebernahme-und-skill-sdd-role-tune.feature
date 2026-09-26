Feature: Ratchet, Übernahme und Skill sdd-role-tune
  Als Entwickler einer Rolle
  möchte ich nur Änderungen übernehmen, die nichts verschlechtern
  um Rollen schrittweise und belegbar zu verbessern

  Scenario: Verbesserung wird angenommen
    Given der Kandidat hat höheren Gesamt- und Holdout-Score und keine Regression
    When ich "sdd role compare base.json kandidat.json" ausführe
    Then ist das Ergebnis "accept" und der Exit-Code 0

  Scenario: Ratchet verhindert Regression
    Given der Kandidat verbessert den Gesamtscore um 0,05
    And Fall DEC-003 fällt von pass auf fail
    When ich "sdd role compare base.json kandidat.json" ausführe
    Then ist das Ergebnis "reject" mit Verweis auf DEC-003 und der Exit-Code 1

  Scenario: Holdout-Score sinkt
    Given der Kandidat hat einen niedrigeren Holdout-Score
    When ich "sdd role compare base.json kandidat.json" ausführe
    Then ist das Ergebnis "reject" ohne Nennung eines Holdout-Falls

  Scenario: Geändertes Ausgabeschema
    Given der Kandidat nennt ein anderes output_schema
    When ich "sdd role compare base.json kandidat.json" ausführe
    Then ist das Ergebnis "reject" mit Verweis auf output_schema

  Scenario: Übernahme einer Prompt-Änderung
    Given die Baseline hat Rollenversion 1.0.0
    And der Report kandidat.json stammt aus einer Kandidatendatei mit geändertem Prompt
    When ich "sdd role accept decomposer --report kandidat.json" ausführe
    Then hat die Rolle Version 1.1.0 und den Prompt des Kandidaten
    And baseline.json nennt 1.1.0 und die Scores aus kandidat.json
    And CHANGELOG.md enthält Score vorher und nachher

  Scenario: Übernahme ohne accept
    Given compare gegen die Baseline ergibt reject
    When ich "sdd role accept decomposer --report kandidat.json" ausführe
    Then ist der Exit-Code 1 und nichts wurde geändert

  Scenario: Erzwungene Übernahme
    When ich "sdd role accept decomposer --report kandidat.json --force --reason 'Rubrik ersetzt'" ausführe
    Then enthält baseline.json forced.reason und CHANGELOG.md den Grund

  Scenario: Skill sdd-role-tune
    Given der Skill sdd-role-tune in Repo und Blueprint
    Then beschreibt er Baseline, eine Änderung mit Hypothese, compare und accept nach Bestätigung
    And er verbietet Änderungen an Fällen und Checks, --include-holdout und das Lesen von holdout-Pfaden
