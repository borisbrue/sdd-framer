# CON-0196 · SPEC-0054 FR-03, FR-04, FR-05, FR-08 bis FR-11
Feature: Score-Berechnung
  Als Supervisor, Pipeline-Gate oder Benchmark
  möchte ich aus Sondenergebnissen reproduzierbar normierte Scores erhalten
  um Codestände und Modelle vergleichen zu können, ohne dass ausgefallene Messungen den Score schönen

  Scenario Outline: Lineare Normierung einer Metrik
    Given die Metrik "<metrik>" hat die Normierung good <good> und bad <bad>
    When der Rohwert <roh> gemessen wird
    Then ist der normierte Wert <norm>

    Examples:
      | metrik        | good | bad | roh  | norm |
      | lint_per_kloc | 0    | 10  | 5    | 0.5  |
      | lint_per_kloc | 0    | 10  | 12   | 0.0  |
      | lint_per_kloc | 0    | 10  | 0    | 1.0  |
      | coverage      | 0.9  | 0.5 | 0.7  | 0.5  |
      | coverage      | 0.9  | 0.5 | 0.95 | 1.0  |

  Scenario: Gewichteter Gesamtscore
    Given requirements hat den Score 1.0, architecture 0.5 und code_quality 0.8
    And die Gewichte sind 0.5, 0.25 und 0.25
    When der Gesamtscore berechnet wird
    Then ist der Gesamtscore 0.825
    And der Report ist nicht als incomplete markiert

  Scenario: Renormierung bei ausgefallener Dimension
    Given requirements hat den Score 1.0 und architecture 0.5
    And alle Metriken von code_quality sind n/a
    When der Gesamtscore berechnet wird
    Then ist code_quality n/a
    And der Gesamtscore ist 0.8333
    And der Wurzelknoten trägt renormalized true
    And der Report ist als incomplete markiert

  Scenario: Anforderungsscore aus FR-Status
    Given die Spec hat 4 FRs mit den Status erfüllt, erfüllt, teilweise, fehlt
    And es liegen keine Holdout-Ergebnisse vor
    When requirements berechnet wird
    Then ist der Score von requirements 0.5

  Scenario Outline: Holdout-Ergebnisse fließen gewichtet ein
    Given der FR-Anteil erfüllt ist 0.5
    And die holdout_pass_rate ist 0.9
    And quality.weights.requirements.holdout ist <h>
    When requirements berechnet wird
    Then ist der Score von requirements <score>

    Examples:
      | h         | score |
      | (Default) | 0.7   |
      | 0.25      | 0.6   |

  Scenario: Ausgefallene Testsonde
    Given die Sonde mit role tests ist ausgefallen
    When requirements berechnet wird
    Then haben alle FRs den Status unbekannt
    And requirements ist n/a

  Scenario Outline: Status eines FR aus seinen Testfällen
    Given FR-07 sind die Testfälle mit den Ergebnissen <ergebnisse> zugeordnet
    When der FR-Status bestimmt wird
    Then ist der Status von FR-07 "<status>"

    Examples:
      | ergebnisse             | status    |
      | passed, passed         | erfüllt   |
      | passed, failed         | teilweise |
      | failed, error          | fehlt     |
      | keine                  | fehlt     |
      | skipped, skipped       | fehlt     |

  Scenario: Architekturscore aus gewichteten Verstößen
    Given quality.architecture.threshold ist 5
    And es gibt 2 Verstöße mit severity error und 2 mit severity warn
    When architecture berechnet wird
    Then ist der Score von architecture 0.5

  Scenario: Baseline-Verstöße zählen als warn
    Given quality.architecture.threshold ist 5
    And es gibt 4 Verstöße mit severity error, die alle in der Baseline stehen
    When architecture berechnet wird
    Then ist der Score von architecture 0.8
    And count.architecture.errors ist 0

  Scenario: Konfigurierbare Severity-Gewichte
    Given quality.architecture.threshold ist 5
    And quality.architecture.severity_weights ist error 1.0 und warn 0.5
    And es gibt 2 Verstöße mit severity error und 2 mit severity warn
    When architecture berechnet wird
    Then ist der Score von architecture 0.4

  Scenario: Architektur ohne Abhängigkeitssonde
    Given quality.yaml enthält keine Sonde mit role deps
    When architecture berechnet wird
    Then ist architecture n/a mit Grund

  Scenario: Zu viele Regeln ohne benötigte Kantenart
    Given architecture.yaml hat 3 Regeln
    And die Sonde mit role deps liefert nur die Kantenart import
    And 2 der Regeln brauchen die Kantenart call oder write
    When architecture berechnet wird
    Then ist architecture n/a
    And rules_na enthält 2 Einträge mit Grund

  Scenario: Exit-Code ungleich 0 mit gültiger Ausgabe ist kein Ausfall
    Given die Sonde "lint" endet mit Exit-Code 1
    And ihre Ergebnisdatei ist gültiges SARIF mit 3 Befunden
    When die Sonde ausgewertet wird
    Then hat die Sonde den Status ok
    And lint_per_kloc wird aus 3 Befunden berechnet

  Scenario: Ausgefallene Metrik-Sonde wird renormiert
    Given code_quality hat die Metriken lint_per_kloc 0.6 und type_errors 1.0 mit Gewicht 1
    And die Sonde für type_errors ist ausgefallen
    When code_quality berechnet wird
    Then ist type_errors n/a mit Grund
    And der Score von code_quality ist 0.6
    And code_quality trägt renormalized true

  Scenario: Judge ohne Gewicht verändert den Score nicht
    Given der Judge-Knoten hat den Score 0.2 und das Gewicht 0
    And requirements 1.0, architecture 1.0, code_quality 1.0
    When der Gesamtscore berechnet wird
    Then ist der Gesamtscore 1.0
    And der Judge-Knoten erscheint im Report mit Modell und Rubrikversion

  Scenario Outline: Gates sind fail-closed
    Given quality.gates enthält "<gate>"
    And der gemessene Wert ist <wert>
    When die Gates ausgewertet werden
    Then ist das Gate <ergebnis>

    Examples:
      | gate                                 | wert | ergebnis        |
      | requirements >= 1.0                  | 1.0  | bestanden       |
      | requirements >= 1.0                  | 0.75 | nicht bestanden |
      | requirements >= 1.0                  | n/a  | nicht bestanden |
      | count.architecture.errors == 0       | 0    | bestanden       |
      | code_quality >= 0.7                  | n/a  | nicht bestanden |
      | code_quality.lint_per_kloc >= 0.5    | 0.6  | bestanden       |

  Scenario Outline: Ungültige Gates sind Konfigurationsfehler
    Given quality.gates enthält "<gate>"
    When die Konfiguration validiert wird
    Then meldet sie einen Fehler "<fehler>"

    Examples:
      | gate                              | fehler                |
      | count.architecture.errors >= 0.8  | ganze Zahl erwartet   |
      | requirements >= 3                 | Wert in [0, 1] erwartet |
      | security >= 0.5                   | unbekannter Pfad      |
