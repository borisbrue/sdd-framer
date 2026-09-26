Feature: Abschluss-Kette, reopen und config test-llm
  Als Nutzer der Dark Factory
  möchte ich den Run mit --auto bis zu PR und Merge laufen lassen
  um orchestrate durch die Pipeline zu ersetzen, ohne einen zweiten Retry-Automaten

  Scenario: Holdout-Ergebnis als Fakt der Abnahme
    Given pipeline.auto_steps enthält holdout und evaluator.base_url ist gesetzt
    When der Run mit --auto alle Tasks abgeschlossen hat
    Then läuft die Holdout-Evaluation vor S3
    And die S3-Anfrage enthält bestandene und fehlgeschlagene Szenarien und die Quote

  Scenario: Holdout ohne Base-URL
    Given pipeline.auto_steps enthält holdout, aber keine Base-URL ist gesetzt
    When der Run S3 erreicht
    Then enthält die S3-Anfrage holdout n/a mit Grund

  Scenario: reopen öffnet Tasks erneut
    Given die S3-Anfrage eines Runs
    When der Supervisor mit reopen für T01 und einem Hinweis antwortet
    Then geht T01 zurück auf red und der nächste Implementer-Aufruf enthält den Hinweis
    And danach wird S3 erneut angefragt

  Scenario: reopen bis zur Grenze
    Given pipeline.max_reopen ist 1
    When der Supervisor zweimal reopen antwortet
    Then hält der Run beim zweiten Mal an

  Scenario: Finalize und Auto-Merge
    Given pipeline.auto_steps enthält finalize und automerge und das Projekt ist ein Git-Repository
    When der Run mit --auto S3 mit vollständiger Abnahme passiert
    Then wird finalize ausgeführt und liefert einen PR
    And automerge fragt das Autonomie-Level ab und labelt oder merged den PR entsprechend

  Scenario: Auto-Merge nicht erlaubt
    Given das Autonomie-Level erlaubt keinen Auto-Merge
    When automerge läuft
    Then bleibt der PR offen und events.jsonl nennt den Grund

  Scenario: Ohne --auto nur finalize
    When ich "sdd pipeline run SPEC-0900" ohne --auto ausführe
    Then läuft nach S3 nur finalize, weder holdout noch automerge

  Scenario: --task mit --auto
    When ich "sdd pipeline run SPEC-0900 --task T01 --auto" ausführe
    Then ist der Exit-Code 2

  Scenario: test-llm prüft Rollen und Profile
    Given llm.profiles lokal und llm.roles.reviewer mit profile lokal
    When ich "sdd config test-llm" ausführe
    Then prüft der Befehl den Endpunkt von lokal genau einmal
    And die Ausgabe nennt Dauer und ob Reasoning-Tokens gemeldet wurden

  Scenario: test-llm überspringt Session-Rollen
    Given llm.roles.implementer.mode ist session
    When ich "sdd config test-llm --role implementer" ausführe
    Then meldet die Ausgabe, dass session nicht geprüft wird, und der Exit-Code ist 0
