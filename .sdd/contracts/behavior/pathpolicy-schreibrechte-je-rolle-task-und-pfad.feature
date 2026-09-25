# CON-0204 · SPEC-0053 FR-07, FR-09
Feature: PathPolicy
  Als Pipeline
  möchte ich jeden Schreibvorgang einer Rolle unabhängig vom Provider prüfen
  um zu garantieren, dass der Supervisor nie schreibt und Rollen nur ihre erlaubten Dateien ändern

  Background:
    Given ein Run für SPEC-0900 mit dem Task "t-1"
    And der Task hat allowed_paths "tool/app/**" und test_file "tests/unit/test_app.py"

  Scenario: Supervisor darf nie schreiben
    When die Rolle supervisor "tool/app/a.py" schreiben will
    Then lehnt die PathPolicy mit Grund "Rolle supervisor schreibt nicht" ab

  Scenario Outline: Geschützte Pfade für alle Rollen
    When die Rolle <rolle> "<pfad>" schreiben will
    Then lehnt die PathPolicy mit Grund "geschützter Pfad" ab

    Examples:
      | rolle       | pfad                          |
      | implementer | .sdd/specs/SPEC-0900.md       |
      | implementer | .sdd/holdout/HOL-0001.md      |
      | test_author | contracts/data/x.schema.json  |
      | implementer | specs/alt.md                  |

  Scenario: implementer darf die Testdatei nicht ändern
    When die Rolle implementer "tests/unit/test_app.py" schreiben will
    Then lehnt die PathPolicy mit Grund "Testdatei des Tasks" ab

  Scenario: test_author schreibt die Testdatei
    When die Rolle test_author "tests/unit/test_app.py" schreiben will
    Then erlaubt die PathPolicy den Schreibvorgang

  Scenario: Pfad außerhalb der erlaubten Pfade
    When die Rolle implementer "tool/other/b.py" schreiben will
    Then lehnt die PathPolicy mit Grund "außerhalb allowed_paths" ab

  Scenario: Erlaubter Pfad
    When die Rolle implementer "tool/app/b.py" schreiben will
    Then erlaubt die PathPolicy den Schreibvorgang

  Scenario: Task ohne allowed_paths
    Given der Task hat keine allowed_paths
    When die Rolle implementer "tool/other/b.py" schreiben will
    Then erlaubt die PathPolicy den Schreibvorgang

  Scenario: Pfadflucht wird erkannt
    When die Rolle implementer "tool/app/../../.sdd/specs/x.md" schreiben will
    Then lehnt die PathPolicy mit Grund "geschützter Pfad" ab

  Scenario: Abgelehnter Schreibvorgang im Protokoll
    When die Rolle implementer "tool/other/b.py" schreiben will
    Then enthält events.jsonl ein Ereignis write_rejected mit Rolle, Pfad und Grund
    And das Ereignis role_call des Rollenaufrufs hat outcome gate_failed
    And die Datei wurde nicht geschrieben

  Scenario Outline: Unabhängig vom Provider
    Given die Rolle implementer nutzt den Provider <provider>
    When sie "tests/unit/test_app.py" schreiben will
    Then lehnt die PathPolicy mit Grund "Testdatei des Tasks" ab

    Examples:
      | provider      |
      | openai-compat |
      | claude-cli    |

  Scenario Outline: Nicht schreibende Rollen werden abgelehnt
    When die Rolle <rolle> "tool/app/a.py" schreiben will
    Then lehnt die PathPolicy mit Grund "Rolle <rolle> schreibt nicht" ab

    Examples:
      | rolle       |
      | reviewer    |
      | decomposer  |
      | doc_writer  |

  Scenario: test_author schreibt nur die Testdatei
    When die Rolle test_author "tool/app/a.py" schreiben will
    Then lehnt die PathPolicy mit Grund "test_author schreibt nur die Testdatei" ab

  Scenario: Projekteigene geschützte Pfade
    Given pipeline.protected_paths enthält "docs/adr/**"
    When die Rolle implementer "docs/adr/ADR-0001.md" schreiben will
    Then lehnt die PathPolicy mit Grund "geschützter Pfad" ab
