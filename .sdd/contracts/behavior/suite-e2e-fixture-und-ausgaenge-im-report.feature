Feature: Suite e2e, Fixture und Ausgänge im Report
  Als Entwickler
  möchte ich Modellbelegungen an ganzen Specs messen
  um die Belegung für echte Pipeline-Runs zu wählen

  Scenario: Ganze Spec auf einem Fixture
    Given eine e2e-Suite mit einem Mini-Fixture und einer Spec
    When ich "sdd bench run --suite e2e --repetitions 1" ausführe
    Then enthält results.jsonl je Belegung einen Record mit q_kind quality, Q_req und Tokens je Rolle
    And das Projekt-Worktree ist unverändert

  Scenario: Versteckte Tests bleiben verborgen
    Given ein Fixture, dessen versteckter Test einen Marker enthält
    When die Rollen aufgerufen werden
    Then enthält kein Prompt den Marker

  Scenario: Budget im e2e-Lauf
    Given das Budget der Matrix ist max_tokens 100
    When der Pipeline-Run mehr verbraucht
    Then endet der Lauf mit halted: budget und der Record enthält den gemessenen Stand

  Scenario: Unbekannte Isolation
    Given die Suite nennt isolation: container
    When ich "sdd bench run --suite e2e" ausführe
    Then ist der Exit-Code 2

  Scenario: Fixture todo-service
    Given das Fixture im Blueprint
    Then hat es drei Specs mit 3, 6 und 10 FRs
    And die Referenzlösung besteht alle versteckten Tests, der Startstand keine

  Scenario: Ausgänge im Report
    Given Records mit Ausgang completed und halted: budget
    When ich "sdd bench report <ordner>" ausführe
    Then nennt der Report je Eintrag die Zahl der Läufe je Ausgang
