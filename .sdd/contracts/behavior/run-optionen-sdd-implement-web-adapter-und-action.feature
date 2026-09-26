Feature: Run-Optionen, sdd-implement, Web-Adapter und Action
  Als Nutzer von sdd-framer
  möchte ich, dass jeder Einstieg einen Run der Pipeline erzeugt
  um überall dasselbe Verhalten, Protokoll und Monitoring zu haben

  Scenario: Session-Rollen pro Run
    Given config.yaml belegt test_author, implementer und supervisor mit LLM-Profilen
    When ich "sdd pipeline run SPEC-0900 --session implementer" ausführe
    Then enthält run.json options.session mit implementer
    And der erste Arbeitsauftrag an implementer endet mit Exit 3 und pending-work.json
    And config.yaml ist unverändert

  Scenario: Unbekannte Session-Rolle
    When ich "sdd pipeline run SPEC-0900 --session tester" ausführe
    Then ist der Exit-Code 2 und die Ausgabe nennt die bekannten Rollen

  Scenario: Schritte pro Run
    When ich "sdd pipeline run SPEC-0900 --auto --steps holdout" ausführe
    Then enthält run.json options.steps mit holdout
    And nach S3 laufen weder finalize noch automerge

  Scenario Outline: Ungültige Schrittangabe
    When ich "<aufruf>" ausführe
    Then ist der Exit-Code 2

    Examples:
      | aufruf                                           |
      | sdd pipeline run SPEC-0900 --steps holdout       |
      | sdd pipeline run SPEC-0900 --auto --steps deploy |

  Scenario: Skill sdd-implement nutzt die Pipeline
    Given der Skill sdd-implement in Repo und Blueprint
    Then sind beide Dateien identisch
    And der Skill ruft "sdd pipeline run $ARGUMENTS --auto --session test_author --session implementer --session supervisor"
    And er beschreibt die Fortsetzung mit "sdd pipeline done" und "sdd pipeline decide"
    And er enthält weder task-route, task-exec, "sdd decompose" noch "sdd finalize"

  Scenario: Web-UI startet einen Pipeline-Run
    When die Web-UI "POST /api/orchestrate" mit spec_id SPEC-0900 aufruft
    Then ist der Statuscode 202 und die Antwort enthält run_id
    And unter .sdd/runs/SPEC-0900 gibt es einen Run mit dieser ID
    And "GET /api/pipeline/<run_id>" liefert run_id, spec_id, status, attempts, max_attempts, log, report und current_step

  Scenario: Web-UI ohne PR
    When die Web-UI "POST /api/orchestrate" mit no_pr true aufruft
    Then läuft der Prozess mit "--steps holdout"
    And report.pr_url ist leer

  Scenario: Web-UI im Probelauf
    When die Web-UI "POST /api/orchestrate" mit dry_run true aufruft
    Then läuft der Prozess mit "--dry-run"

  Scenario: Web-UI bricht ab
    Given ein laufender Run aus der Web-UI
    When die Web-UI "POST /api/pipeline/<run_id>/abort" aufruft
    Then ist der Prozess beendet und der Status aborted

  Scenario: Web-UI wartet auf Claude
    Given config.yaml belegt supervisor mit mode session
    When die Web-UI einen Run startet und S1 erreicht wird
    Then ist der Status paused
    And das Log nennt "sdd pipeline decide"

  Scenario: sdd start --auto
    When ich "sdd start SPEC-0900 --auto --no-container" ausführe
    Then gibt es unter .sdd/runs/SPEC-0900 einen neuen Run
    And der Exit-Code ist der des Pipeline-Runs

  Scenario: GitHub-Action-Vorlage
    Given die Vorlage sdd-orchestrate.yml in Repo und Blueprint
    Then ruft sie "sdd pipeline run" mit "--auto"
    And sie ruft nicht "sdd orchestrate"
    And ANTHROPIC_API_KEY ist nicht als Pflicht-Secret gesetzt
