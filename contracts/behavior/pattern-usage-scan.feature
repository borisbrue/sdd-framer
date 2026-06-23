Feature: Pattern-Usage-Aggregation (Katalog + Code-Scan)
  Als Entwickler:in will ich die akzeptierten Patterns mit ihren Code-Fundstellen sehen,
  damit verwendete Design-Entscheidungen sichtbar und nachvollziehbar sind. (SPEC-0049)

  Background:
    Given ein Katalog mit dem akzeptierten Pattern "Strategy" für "SPEC-0015"
    And die Source-Roots "tool/sdd_cli/" und "web/"

  Scenario: Akzeptiertes Pattern mit Annotation erhält Code-Fundstellen
    Given eine Quelldatei "tool/sdd_cli/routing.py" mit der Annotation "Strategy Pattern (Refactoring Guru): ..." in Zeile 3
    When die Pattern-Usage aggregiert wird
    Then enthält das Ergebnis das Pattern "Strategy"
    And dessen "code_locations" enthält genau einen Eintrag mit file "tool/sdd_cli/routing.py" und line 3

  Scenario: Akzeptiertes Pattern ohne Annotation erscheint mit leerer Fundstellenliste
    Given keine Quelldatei enthält eine Annotation für "Strategy"
    When die Pattern-Usage aggregiert wird
    Then enthält das Ergebnis das Pattern "Strategy"
    And dessen "code_locations" ist eine leere Liste

  Scenario: Namens-Normalisierung verbindet Annotation und Katalog
    Given der Katalog enthält das akzeptierte Pattern "ChainOfResponsibility"
    And eine Quelldatei mit der Annotation "Chain of Responsibility Pattern: ..."
    When die Pattern-Usage aggregiert wird
    Then wird die Fundstelle dem Pattern "ChainOfResponsibility" zugeordnet

  Scenario: Suggested- und Rejected-Patterns werden ausgeschlossen
    Given der Katalog enthält ein "suggested" Pattern "Observer" und ein "rejected" Pattern "Singleton"
    When die Pattern-Usage aggregiert wird
    Then enthält das Ergebnis weder "Observer" noch "Singleton"

  Scenario: Annotation ohne Katalogeintrag wird ignoriert
    Given eine Quelldatei mit der Annotation "Visitor Pattern: ..."
    And der Katalog enthält kein akzeptiertes Pattern "Visitor"
    When die Pattern-Usage aggregiert wird
    Then enthält das Ergebnis kein Pattern "Visitor"

  Scenario: Leerer Katalog liefert leere Aggregation
    Given der Katalog enthält keine akzeptierten Patterns
    When die Pattern-Usage aggregiert wird
    Then ist das Ergebnis eine leere Liste
