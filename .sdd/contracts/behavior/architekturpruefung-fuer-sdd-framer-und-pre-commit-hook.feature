Feature: Architekturprüfung für sdd-framer und Pre-Commit-Hook
  Als Maintainer von sdd-framer
  möchte ich, dass die Architekturentscheidungen bei jedem Lauf maschinell geprüft werden
  um zu verhindern, dass die bereinigte Struktur wieder zerfällt

  Scenario: Main ist grün trotz Altlasten
    Given der Repo-Stand von sdd-framer mit .sdd/architecture.yaml und Baseline
    When ich "sdd arch check" ausführe
    Then ist der Exit-Code 0
    And die Ausgabe listet ARCH-04 in tool/sdd_cli/local_agent.py als "warn (Baseline, SPEC-0058)"

  Scenario: Jede Regel ist an ein akzeptiertes ADR gebunden
    Given die Regeln ARCH-01 bis ARCH-04 in .sdd/architecture.yaml
    When ich die verknüpften ADRs lese
    Then hat jedes ADR den Status accepted und nennt seine Regel in enforced_by
    And "sdd validate" meldet keinen ADR-Verknüpfungsfehler

  Scenario: Die Baseline enthält keinen ARCH-03-Eintrag
    Given die Baseline .sdd/quality/arch-baseline.json
    When ich ihre Einträge lese
    Then gibt es keinen Eintrag für ARCH-03
    And jeder Eintrag hat einen Grund

  Scenario: Neuer Verstoß blockiert
    Given eine Kopie des Repos, in der tool/sdd_cli/web/api/routes/new.py aus tool/sdd_cli/llm/providers/openai_compat.py importiert
    When ich "sdd arch check" ausführe
    Then ist der Exit-Code 1
    And die Ausgabe nennt ARCH-03 und ADR-0004

  Scenario: Unaufgelöster Schreibzugriff aus der Web-API
    Given eine Kopie des Repos, in der tool/sdd_cli/web/api/routes/new.py mit Path(ziel).write_text(...) schreibt
    When ich "sdd arch check" ausführe
    Then ist der Exit-Code 1
    And die Ausgabe nennt ARCH-01 und pathlib.Path.write_text

  Scenario: Ohne Option bleibt write_ownership beim alten Verhalten
    Given eine Regel write_ownership ohne unresolved
    When eine Datei außerhalb der owners mit unaufgelöstem Ziel schreibt
    Then meldet die Regel keinen Verstoß

  Scenario: Pre-Commit-Hook blockiert einen Architekturverstoß
    Given ein Projekt mit .sdd/architecture.yaml und einer gestagten .py-Datei mit Verstoß
    When der Pre-Commit-Hook läuft
    Then ist sein Exit-Code 1
    And die Ausgabe nennt die verletzte Regel

  Scenario: Pre-Commit-Hook ohne Architekturregeln
    Given ein Projekt ohne .sdd/architecture.yaml
    When der Pre-Commit-Hook läuft
    Then führt er keine Architekturprüfung aus

  Scenario: Architekturprüfung im Hook abgeschaltet
    Given quality.arch_pre_commit ist false
    When der Pre-Commit-Hook mit einer gestagten .py-Datei mit Verstoß läuft
    Then führt er keine Architekturprüfung aus

  Scenario: Laufzeit der Prüfung
    Given der Repo-Stand von sdd-framer
    When ich "sdd arch check" ausführe
    Then dauert die Prüfung weniger als 10 Sekunden
