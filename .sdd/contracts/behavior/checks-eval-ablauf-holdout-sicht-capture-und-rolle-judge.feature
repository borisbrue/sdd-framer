Feature: Checks, Eval-Ablauf, Holdout-Sicht, capture und Rolle judge
  Als Entwickler einer Rolle
  möchte ich sie reproduzierbar gegen Golden Cases messen
  um Prompt-Änderungen belegbar zu bewerten

  Scenario: Eval über sichtbare und Holdout-Fälle
    Given die Rolle decomposer hat 5 sichtbare und 3 Holdout-Fälle
    When ich "sdd role eval decomposer --model lokal --runs 3 --json" ausführe
    Then enthält der Report 5 Fälle mit Details und ein Holdout-Aggregat mit 3 Fällen
    And jeder Lauf hat input_tokens, output_tokens und reasoning_tokens
    And das Projektverzeichnis ist unverändert

  Scenario: Holdout bleibt verborgen
    When ich "sdd role eval decomposer" ausführe
    Then nennt die Ausgabe keine ID und keinen Inhalt eines Holdout-Falls

  Scenario: Holdout-Szenarien ignorieren Rollen-Fälle
    Given unter .sdd/holdout/roles/decomposer liegt ein Fall mit input/spec.md
    When ich "sdd holdout run --base-url http://x --spec SPEC-0900" ausführe
    Then wird kein Szenario aus .sdd/holdout/roles gelesen

  Scenario Outline: Check mit Positiv- und Negativfall
    Given ein Fall mit Check "<check>"
    When die Ausgabe "<ausgabe>" bewertet wird
    Then ist das Ergebnis "<ergebnis>"

    Examples:
      | check                  | ausgabe                         | ergebnis |
      | task_count             | 3 Tasks bei min 4               | fail     |
      | ordered_before         | Datenmodell vor API-Endpunkt    | pass     |
      | red_against_stub       | Test grün gegen den Stub        | fail     |
      | green_against_reference| Test grün gegen die Referenz    | pass     |
      | mutation_kill_rate     | 2 von 4 Mutanten getötet        | fail     |
      | hidden_tests_pass      | versteckte Tests grün           | pass     |
      | seeded_bug_recall      | Befund an der eingebauten Stelle| pass     |
      | clean_diff_precision   | Befund an einem fehlerfreien Diff | fail   |
      | decision_matches       | revise statt approve            | fail     |

  Scenario: Zeitüberschreitung eines Tests
    Given ein Fall, dessen test_command länger als timeout_seconds läuft
    When ich "sdd role eval implementer --case IMP-001" ausführe
    Then ist der Check hidden_tests_pass "fail" mit Grund Zeitlimit

  Scenario: Gate nutzt nur gate-fähige Checks
    Given eine Rolle nennt den Check hidden_tests_pass in checks
    When ich "sdd validate" ausführe
    Then meldet die Prüfung den Check als im Gate nicht nutzbar

  Scenario: Fall aus einem Pipeline-Fehlschlag
    Given Run r-42 enthält eine S1-Entscheidung "revise" mit Request-ID req-3
    When ich "sdd role case capture r-42 req-3" ausführe
    Then existiert ein neuer Fall SUP-xxx mit draft: true und Check decision_matches
    And der Fall zählt nicht im nächsten Eval

  Scenario: Capture mit unbekannter ID
    When ich "sdd role case capture r-42 req-999" ausführe
    Then ist der Exit-Code 2

  Scenario: Judge bewertet blind
    Given ein Fall mit Rubrik-Item granularity
    When ich "sdd role eval decomposer --model lokal" ausführe
    Then enthält der Prompt an den Judge weder "lokal" noch die Rollenversion
    And der Report nennt Judge-Modell und Rubrikversion

  Scenario: sdd quality --judge nutzt die Rolle judge
    Given llm.roles.judge ist mit einem Profil belegt
    When ich "sdd quality measure --judge" ausführe
    Then ruft der Judge dieses Profil auf
