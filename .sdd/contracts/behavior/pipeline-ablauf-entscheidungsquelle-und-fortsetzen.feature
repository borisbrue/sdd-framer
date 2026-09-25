# CON-0205 · SPEC-0053 FR-04..FR-06, FR-08, FR-10..FR-16
Feature: Pipeline-Ablauf, Entscheidungsquelle und Fortsetzen
  Als Nutzer der Rollen-Pipeline
  möchte ich, dass lokale Modelle arbeiten und der Supervisor nur an festen Punkten entscheidet
  um Claude-Tokens zu sparen, ohne Kontrolle über Freigaben und Abnahme zu verlieren

  Background:
    Given ein Projekt mit der freigegebenen Spec SPEC-0900 mit FR-01 und FR-02
    And alle Rollen nutzen Fake-Provider mit vorbereiteten Antworten

  Scenario: Dry-Run zerlegt und fragt nur S1 an
    When ich "sdd pipeline run SPEC-0900 --dry-run" ausführe
    Then ist der decomposer genau einmal aufgerufen worden
    And decisions.jsonl enthält genau eine Entscheidung für S1
    And kein test_author- oder implementer-Aufruf hat stattgefunden

  Scenario: Rollen-Check fehlgeschlagen vor S1
    Given die erste Zerlegung deckt FR-02 nicht ab
    When ich "sdd pipeline run SPEC-0900 --dry-run" ausführe
    Then wird der decomposer mit der Meldung des Checks fr_coverage erneut aufgerufen
    And S1 wird erst nach einer vollständigen Zerlegung angefragt

  Scenario: revise bis zur Grenze
    Given der Supervisor antwortet in S1 dreimal mit revise
    When ich "sdd pipeline run SPEC-0900" ausführe
    Then hat state.json den status halted
    And die Pipeline hat höchstens zweimal neu zerlegt

  Scenario: RED-Gate verwirft einen grünen Test
    Given der test_author liefert einen Test, der ohne Implementierung grün ist
    When der Task bearbeitet wird
    Then wird der Test verworfen und test_author erneut aufgerufen

  Scenario: Eskalation nach max_attempts
    Given der implementer scheitert dreimal am Review für Task t-1
    When der Supervisor in S2 mit "reassign" auf das Modell m2 antwortet
    Then bearbeitet m2 den Task t-1 als implementer
    And state.json zeigt für t-1 den Zustand reassigned und danach green

  Scenario: retry_with_hint gibt den Hinweis weiter
    Given der Supervisor antwortet in S2 mit retry_with_hint "Typ int statt str"
    When t-1 erneut bearbeitet wird
    Then enthält der Kontext des implementer die Quelle history mit "Typ int statt str"

  Scenario: S3 blockiert Finalize bei fehlender FR
    Given alle Tasks sind done
    When der Supervisor in S3 FR-02 als fehlt meldet
    Then wird finalize nicht aufgerufen
    And state.json hat den status halted

  Scenario: Ungültige Entscheidung
    Given der Supervisor antwortet in S1 zweimal mit einem ungültigen Command
    When ich "sdd pipeline run SPEC-0900" ausführe
    Then enthält decisions.jsonl zwei Einträge mit valid false
    And state.json hat den status halted

  Scenario: Dialogmodus hält an und setzt fort
    Given llm.roles.supervisor.mode ist session
    When ich "sdd pipeline run SPEC-0900" ausführe
    Then ist der Exit-Code 3
    And pending-decision.json enthält point S1 und allowed_commands approve, revise, halt
    And state.json hat den status awaiting_supervisor
    When ich "sdd pipeline decide <run> --json {\"point\":\"S1\",\"command\":\"approve\",\"reason\":\"ok\"}" ausführe
    Then ist state.pending_request_id leer
    And die Anfrage liegt unter requests/<request_id>.json
    And die Zeile in decisions.jsonl nennt dieselbe request_id
    And der Run läuft ab der Phase tasks weiter

  Scenario: decide ohne offene Anfrage
    Given ein Run ohne offene Anfrage
    When ich "sdd pipeline decide <run> --json {...}" ausführe
    Then ist der Exit-Code 2

  Scenario: decide mit unzulässigem Command
    Given eine offene Anfrage für S1
    When ich "sdd pipeline decide <run> --json {\"point\":\"S2\",\"command\":\"redecompose\",\"reason\":\"x\"}" ausführe
    Then ist der Exit-Code 2
    And pending-decision.json besteht weiter

  Scenario: Fortsetzen nach Abbruch
    Given ein Run wurde während Task t-2 abgebrochen
    When ich "sdd pipeline run SPEC-0900 --resume <run>" ausführe
    Then werden bereits erledigte Tasks nicht erneut bearbeitet
    And t-2 beginnt mit dem nächsten Versuch

  Scenario: Modellserver nicht erreichbar
    Given der Provider des implementer ist nicht erreichbar
    When t-1 bearbeitet wird
    Then hat der Rollenaufruf outcome error
    And nach max_attempts wird S2 angefragt

  Scenario: Längenabbruch des Thinking-Modells
    Given der decomposer antwortet mit finish_reason length und leerem Inhalt
    When die Zerlegung läuft
    Then wird genau einmal mit dem 1,5-fachen Ausgabebudget wiederholt

  Scenario: Warnung bei gleichem Modell
    Given reviewer und implementer nutzen dasselbe Modell am selben Endpunkt
    When ich "sdd pipeline run SPEC-0900 --dry-run" ausführe
    Then enthält run.json die Warnung "Modell reviewt seine eigene Arbeit"

  Scenario: Rückwärtskompatibilität ohne llm.roles
    Given config.yaml enthält keinen Block llm.roles
    When ich "sdd decompose SPEC-0900" ausführe
    Then wird der Provider aus llm.completion verwendet

  Scenario: Usage mit Rollenkontext
    When ich "sdd pipeline run SPEC-0900 --dry-run" ausführe
    Then enthält token_usage je Rollenaufruf einen Datensatz mit role, run_id, attempt und outcome
