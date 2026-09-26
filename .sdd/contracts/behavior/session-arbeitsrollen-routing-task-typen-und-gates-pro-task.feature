Feature: Session-Arbeitsrollen, Routing, Task-Typen und Gates pro Task
  Als Entwickler mit Claude Code und lokalen Modellen
  möchte ich Rollen im Dialog oder nach Komplexität belegen
  um jede Arbeitsweise der alten Pfade mit der Pipeline abzudecken

  Scenario: Implementer im Dialog
    Given llm.roles.implementer.mode ist session
    When der Run den Implementer für T01 erreicht
    Then ist der Exit-Code 3 und state.status ist awaiting_session
    And pending-work.json nennt Rolle implementer, T01 und die erlaubten Pfade
    And es wurde kein LLM für den Implementer aufgerufen

  Scenario: Bestätigung setzt den Run fort
    Given ein offener Auftrag an den Implementer für T01
    When die Session die erlaubte Datei schreibt und "sdd pipeline done <run>" ausführt
    Then wertet die Pipeline das GREEN-Gate aus und setzt mit dem Reviewer fort
    And der Auftrag liegt unter requests/<request_id>.json

  Scenario: Reviewer im Dialog mit JSON-Ausgabe
    Given llm.roles.reviewer.mode ist session und ein offener Auftrag an den Reviewer
    When ich "sdd pipeline done <run> --json '{\"verdict\": \"pass\", \"findings\": []}'" ausführe
    Then gilt der Task als reviewed

  Scenario: Ungültige Bestätigung
    Given ein offener Auftrag an den Reviewer
    When ich "sdd pipeline done <run> --json '{\"verdict\": \"vielleicht\"}'" ausführe
    Then ist der Exit-Code 2 und der Auftrag bleibt offen

  Scenario: done ohne offenen Auftrag
    Given ein Run ohne offenen Session-Auftrag
    When ich "sdd pipeline done <run>" ausführe
    Then ist der Exit-Code 2

  Scenario: Rollenvertrag bei Schreibzugriff außerhalb der erlaubten Pfade
    Given ein offener Auftrag an den Implementer für T01
    When die Session zusätzlich eine Datei außerhalb der erlaubten Pfade schreibt und bestätigt
    Then enthält events.jsonl ein write_rejected mit dieser Datei
    And der Versuch zählt als gate_failed
    And der nächste Auftrag nennt die Datei zum Zurücksetzen

  Scenario: Routing nach Komplexität
    Given llm.profiles lokal und stark und by_complexity low=lokal, high=stark für den Implementer
    When ein Task low und ein Task high bearbeitet werden
    Then ruft der Implementer für den Task low das Modell von lokal und für den Task high das Modell von stark auf

  Scenario: Routing auf session
    Given by_complexity high=session für den Implementer
    When der Implementer einen Task high erreicht
    Then entsteht ein Session-Auftrag statt eines LLM-Aufrufs

  Scenario: Unbekanntes Profil
    Given by_complexity nennt ein Profil, das in llm.profiles fehlt
    When ich "sdd pipeline run SPEC-0900" ausführe
    Then ist der Exit-Code 2

  Scenario: Einzelner Task
    Given eine gespeicherte Zerlegung mit T01 und T02
    When ich "sdd pipeline run SPEC-0900 --task T02" ausführe
    Then wird nur T02 bearbeitet, ohne Zerlegung, S1 und S3

  Scenario: Einzelner Task ohne Zerlegung
    Given keine gespeicherte Zerlegung
    When ich "sdd pipeline run SPEC-0900 --task T01" ausführe
    Then ist der Exit-Code 2

  Scenario: Doku-Task ohne RED-Gate
    Given ein Task vom Typ doc
    When die Pipeline ihn bearbeitet
    Then wird kein test_author aufgerufen und die Testsuite darf keine neuen Fehler haben

  Scenario: Architektur-Gate pro Task
    Given pipeline.task_gates enthält architecture und .sdd/architecture.yaml verbietet einen Import
    When der Implementer diesen Import schreibt
    Then zählt der Versuch als gate_failed und die Datei wird zurückgesetzt

  Scenario: Gate ohne Konfiguration
    Given pipeline.task_gates enthält architecture, aber es gibt keine .sdd/architecture.yaml
    When der Implementer einen Task bearbeitet
    Then ist das Gate n/a und blockiert nicht
