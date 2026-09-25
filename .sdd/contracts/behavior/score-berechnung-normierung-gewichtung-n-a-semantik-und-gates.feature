# language: de
# CON-0196 · SPEC-0054 FR-03, FR-04, FR-05, FR-08 bis FR-11
Funktionalität: Score-Berechnung
  Als Supervisor, Pipeline-Gate oder Benchmark
  möchte ich aus Sondenergebnissen reproduzierbar normierte Scores erhalten
  um Codestände und Modelle vergleichen zu können, ohne dass ausgefallene Messungen den Score schönen

  Szenariogrundriss: Lineare Normierung einer Metrik
    Angenommen die Metrik "<metrik>" hat die Normierung good <good> und bad <bad>
    Wenn der Rohwert <roh> gemessen wird
    Dann ist der normierte Wert <norm>

    Beispiele:
      | metrik        | good | bad | roh  | norm |
      | lint_per_kloc | 0    | 10  | 5    | 0.5  |
      | lint_per_kloc | 0    | 10  | 12   | 0.0  |
      | lint_per_kloc | 0    | 10  | 0    | 1.0  |
      | coverage      | 0.9  | 0.5 | 0.7  | 0.5  |
      | coverage      | 0.9  | 0.5 | 0.95 | 1.0  |

  Szenario: Gewichteter Gesamtscore
    Angenommen requirements hat den Score 1.0, architecture 0.5 und code_quality 0.8
    Und die Gewichte sind 0.5, 0.25 und 0.25
    Wenn der Gesamtscore berechnet wird
    Dann ist der Gesamtscore 0.825
    Und der Report ist nicht als incomplete markiert

  Szenario: Renormierung bei ausgefallener Dimension
    Angenommen requirements hat den Score 1.0 und architecture 0.5
    Und alle Metriken von code_quality sind n/a
    Wenn der Gesamtscore berechnet wird
    Dann ist code_quality n/a
    Und der Gesamtscore ist 0.8333
    Und der Wurzelknoten trägt renormalized true
    Und der Report ist als incomplete markiert

  Szenario: Anforderungsscore aus FR-Status
    Angenommen die Spec hat 4 FRs mit den Status erfüllt, erfüllt, teilweise, fehlt
    Und es liegen keine Holdout-Ergebnisse vor
    Wenn requirements berechnet wird
    Dann ist der Score von requirements 0.5

  Szenario: Holdout-Ergebnisse fließen zur Hälfte ein
    Angenommen der FR-Anteil erfüllt ist 0.5
    Und die holdout_pass_rate ist 0.9
    Wenn requirements berechnet wird
    Dann ist der Score von requirements 0.7

  Szenario: Ausgefallene Testsonde
    Angenommen die Sonde "tests" ist ausgefallen
    Wenn requirements berechnet wird
    Dann haben alle FRs den Status unbekannt
    Und requirements ist n/a

  Szenariogrundriss: Status eines FR aus seinen Testfällen
    Angenommen FR-07 sind die Testfälle mit den Ergebnissen <ergebnisse> zugeordnet
    Wenn der FR-Status bestimmt wird
    Dann ist der Status von FR-07 "<status>"

    Beispiele:
      | ergebnisse             | status    |
      | passed, passed         | erfüllt   |
      | passed, failed         | teilweise |
      | failed, error          | fehlt     |
      | keine                  | fehlt     |
      | skipped, skipped       | fehlt     |

  Szenario: Architekturscore aus gewichteten Verstößen
    Angenommen quality.architecture.threshold ist 5
    Und es gibt 2 Verstöße mit severity error und 2 mit severity warn
    Wenn architecture berechnet wird
    Dann ist der Score von architecture 0.5

  Szenario: Baseline-Verstöße zählen als warn
    Angenommen quality.architecture.threshold ist 5
    Und es gibt 4 Verstöße mit severity error, die alle in der Baseline stehen
    Wenn architecture berechnet wird
    Dann ist der Score von architecture 0.8
    Und architecture.errors ist 0

  Szenario: Zu viele Regeln ohne benötigte Kantenart
    Angenommen architecture.yaml hat 3 Regeln
    Und die Sonde "deps" liefert nur die Kantenart import
    Und 2 der Regeln brauchen die Kantenart call oder write
    Wenn architecture berechnet wird
    Dann ist architecture n/a
    Und rules_na enthält 2 Einträge mit Grund

  Szenario: Exit-Code ungleich 0 mit gültiger Ausgabe ist kein Ausfall
    Angenommen die Sonde "lint" endet mit Exit-Code 1
    Und ihre Ergebnisdatei ist gültiges SARIF mit 3 Befunden
    Wenn die Sonde ausgewertet wird
    Dann hat die Sonde den Status ok
    Und lint_per_kloc wird aus 3 Befunden berechnet

  Szenariogrundriss: Sondenausfall
    Angenommen die Sonde "lint" <fehlerbild>
    Wenn die Sonde ausgewertet wird
    Dann hat die Sonde den Status n/a mit Grund "<grund>"

    Beispiele:
      | fehlerbild                                       | grund                    |
      | verweist auf einen nicht installierten Befehl    | Befehl nicht gefunden    |
      | überschreitet timeout_seconds                    | Zeitlimit überschritten  |
      | schreibt keine Datei nach {out}                  | keine Ausgabe            |
      | schreibt ungültiges SARIF nach {out}             | Ausgabe nicht parsebar   |
      | enthält einen Pfad unter .sdd/holdout/           | Holdout-Pfad verboten    |

  Szenario: Judge ohne Gewicht verändert den Score nicht
    Angenommen der Judge-Knoten hat den Score 0.2 und das Gewicht 0
    Und requirements 1.0, architecture 1.0, code_quality 1.0
    Wenn der Gesamtscore berechnet wird
    Dann ist der Gesamtscore 1.0
    Und der Judge-Knoten erscheint im Report mit Modell und Rubrikversion

  Szenariogrundriss: Gates sind fail-closed
    Angenommen quality.gates enthält "<gate>"
    Und der gemessene Wert ist <wert>
    Wenn die Gates ausgewertet werden
    Dann ist das Gate <ergebnis>

    Beispiele:
      | gate                      | wert | ergebnis        |
      | requirements >= 1.0       | 1.0  | bestanden       |
      | requirements >= 1.0       | 0.75 | nicht bestanden |
      | requirements >= 1.0       | n/a  | nicht bestanden |
      | architecture.errors == 0  | 0    | bestanden       |
      | code_quality >= 0.7       | n/a  | nicht bestanden |
