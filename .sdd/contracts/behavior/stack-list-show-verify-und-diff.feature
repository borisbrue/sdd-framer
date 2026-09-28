Feature: stack list, show, verify und diff
  Als Entwickler
  möchte ich sehen, welche Vorlagen es gibt und ob mein Projekt messbar eingerichtet ist
  um Lücken in der Toolchain früh zu finden

  Scenario: Vorlagen aus allen Quellen
    Given eine Nutzervorlage python-cli und die Blueprint-Vorlage python-cli
    When ich "sdd stack list" ausführe
    Then erscheint python-cli aus der Nutzerquelle und die Blueprint-Vorlage als verdeckt

  Scenario: Vorlage anzeigen
    When ich "sdd stack show python-fastapi" ausführe
    Then nennt die Ausgabe Version, Werkzeuge, Platzhalter und Dateien

  Scenario: Unbekannte Vorlage
    When ich "sdd stack show gibtsnicht" ausführe
    Then ist der Exit-Code 2

  Scenario: Verify grün
    Given ein Projekt aus "sdd init --stack python-cli" mit installierten Werkzeugen
    When ich "sdd stack verify" ausführe
    Then sind alle Pflichtpunkte ok und der Exit-Code ist 0

  Scenario: Verify mit fehlendem Werkzeug
    Given die angewendete Vorlage verlangt ein Werkzeug, das fehlt
    When ich "sdd stack verify" ausführe
    Then nennt die Ausgabe den Installationshinweis und der Exit-Code ist 1

  Scenario: Verify ohne FR-markierten Test
    Given die Test-Sonde meldet keinen FR-markierten Test
    When ich "sdd stack verify" ausführe
    Then scheitert dieser Pflichtpunkt

  Scenario: Diff nach Weiterentwicklung
    Given das Projekt hat .sdd/quality.yaml geändert und die Vorlage hat tests/test_skeleton.py geändert
    When ich "sdd stack diff" ausführe
    Then steht quality.yaml unter vom Projekt geändert und test_skeleton.py unter in der Vorlage neu oder geändert
