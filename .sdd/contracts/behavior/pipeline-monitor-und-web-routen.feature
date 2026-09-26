Feature: Pipeline-Monitor und Web-Routen
  Als Nutzer der Web-UI
  möchte ich Pipeline-Runs im Monitor sehen und aus der UI starten
  um den Fortschritt der Rollen ohne Terminal zu verfolgen

  Scenario: Leseschnittstelle listet Runs
    Given zwei Runs unter .sdd/runs/
    When monitor.list_runs gelesen wird
    Then enthält die Liste beide Runs mit run_id, spec_id, status und started_at, neuester zuerst

  Scenario: Ereignisse eines Tasks im DagEvent-Format
    Given ein Run mit einem role_call und einer Transition für Task T01
    When monitor.task_events ab Offset 0 gelesen wird
    Then hat jedes Ereignis run_id, task_id, status, agent, model, timestamp und details
    And status ist einer von pending, running, done, failed, skipped, paused

  Scenario: Offset liefert nur neue Ereignisse
    Given ein Run, dessen events.jsonl nach dem ersten Lesen wächst
    When monitor.task_events mit dem zurückgegebenen Offset gelesen wird
    Then enthält das Ergebnis nur die neuen Ereignisse

  Scenario: Monitor zeigt einen Pipeline-Run
    Given ein abgeschlossener Run von "sdd pipeline run SPEC-0900 --dry-run"
    When die Web-UI "/api/orchestrate/runs" abfragt
    Then enthält die Antwort den Run mit spec_id SPEC-0900 und status done

  Scenario: Stream eines abgeschlossenen Runs
    Given ein abgeschlossener Pipeline-Run mit Task-Ereignissen
    When die Web-UI "/api/orchestrate/stream/<run_id>" abfragt
    Then liefert der Stream die Task-Ereignisse als SSE-Daten im DagEvent-Format
    And der Stream endet

  Scenario: Projekt ohne Runs
    Given ein Projekt ohne .sdd/runs/
    When die Web-UI "/api/orchestrate/runs" abfragt
    Then ist die Antwort eine leere Liste

  Scenario: Befehls-Route ist abgelöst
    When die Web-UI "POST /api/orchestrate/command/<run_id>" aufruft
    Then ist der Status 410
    And die Antwort nennt "sdd pipeline decide"

  Scenario: Status als JSON
    Given ein Run, der auf eine Entscheidung wartet
    When ich "sdd pipeline status <run_id> --json" ausführe
    Then enthält die Ausgabe status, phase, tasks und die offene Anfrage als JSON

  Scenario: Implement-Route startet die Pipeline
    When die Web-UI "POST /api/specs/SPEC-0900/implement" aufruft
    Then startet sie "sdd pipeline run SPEC-0900" im Hintergrund
    And die Antwort hat die Felder ok und output

  Scenario: Evaluate-Route startet die Holdout-Evaluation
    Given evaluator.base_url ist gesetzt
    When die Web-UI "POST /api/specs/SPEC-0900/evaluate" aufruft
    Then startet sie "sdd holdout run --base-url <url> --spec SPEC-0900" im Hintergrund
