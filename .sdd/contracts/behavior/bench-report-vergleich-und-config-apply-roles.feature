Feature: Bench-Report, Vergleich und config apply-roles
  Als Entwickler
  möchte ich Benchmark-Ergebnisse vergleichbar auswerten und übernehmen
  um die Modellbelegung belegt zu wählen

  Scenario: Report je Rolle mit Pareto-Front
    Given Records für drei implementer-Profile mit q_kind quality
    When ich "sdd bench report <ordner> --by role" ausführe
    Then zeigt report.md für implementer drei Profile mit Q, T_in, T_out und T_reason
    And markiert die Profile auf der Pareto-Front

  Scenario: Nicht unterscheidbar
    Given zwei Belegungen mit Q 0,80 ± 0,05 und 0,82 ± 0,05
    When ich "sdd bench report <ordner>" ausführe
    Then werden beide als nicht unterscheidbar markiert

  Scenario: Getrennte q_kind
    Given Records mit q_kind eval und quality im selben Ordner
    When ich "sdd bench report <ordner>" ausführe
    Then erscheinen zwei Abschnitte ohne gemeinsames Ranking

  Scenario: Geschätzte Tokens
    Given ein Record mit estimated true
    When ich "sdd bench report <ordner>" ausführe
    Then sind seine Tokens mit einem Sternchen markiert

  Scenario: Vergleich mit getauschtem Modell
    Given zwei Ergebnisordner, in denen Profil lokal verschiedene server_model meldet
    When ich "sdd bench compare a b" ausführe
    Then zeigt die Ausgabe je Belegung das Delta und warnt vor dem getauschten Modell

  Scenario: Belegung übernehmen
    Given ein Ergebnisordner mit Belegung all-qwen
    When ich "sdd config apply-roles --from <ordner> --assignment all-qwen --yes" ausführe
    Then enthält config.yaml unter llm.roles die Profile der Belegung
    And die übrigen Einträge und Kommentare sind unverändert

  Scenario: Übernahme ohne Bestätigung
    When ich "sdd config apply-roles --from <ordner> --assignment all-qwen" ausführe und ablehne
    Then bleibt config.yaml unverändert
