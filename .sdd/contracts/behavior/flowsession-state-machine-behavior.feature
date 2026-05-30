# language: de
Funktionalität: FlowSession State Machine – Geführte Agentic Flows
  Als Entwickler mit Smartphone
  möchte ich Agentic Flows über die PWA steuern
  um SDD-Befehle ohne Terminal-Zugang auszuführen

  Hintergrund:
    Angenommen der SDD-Server läuft und ist über Tunnel erreichbar
    Und der Nutzer ist per PWA verbunden

  Szenario: Happy Path – neuer Spec von Anfang bis Ende
    Angenommen der Nutzer startet einen Flow mit flow_type "new-spec"
    Dann gibt der Server eine session_id und den ersten Prompt zurück
    Und der State ist "awaiting_input"
    Wenn der Nutzer alle Schritte nacheinander beantwortet
    Dann erreicht der Flow den State "done"
    Und die Spec ist auf dem Server angelegt

  Szenario: Review-Flow delegiert an SPEC-0016-JobStore
    Angenommen der Nutzer startet einen Flow mit flow_type "review" und spec_id "SPEC-0032"
    Wenn der Flow alle Eingaben abgeschlossen hat
    Dann antwortet der Server mit done=true und einer job_id
    Und die job_id referenziert einen SPEC-0016-AnalysisJob
    Und der Nutzer kann den Job-Status über GET /api/docs/SPEC-0032/analyze/status/{job_id} abfragen

  Szenario: Implement-Flow delegiert an SPEC-0007-Orchestrator
    Angenommen der Nutzer startet einen Flow mit flow_type "implement" und spec_id "SPEC-0032"
    Und SPEC-0032 hat den Status "approved"
    Wenn der Flow alle Eingaben abgeschlossen hat
    Dann antwortet der Server mit done=true und einer job_id
    Und die job_id referenziert einen SPEC-0007-PipelineRun
    Und der Nutzer kann den Job-Status über GET /api/pipeline/{job_id} abfragen

  Szenario: Decision Point pausiert den Flow (FR-05)
    Angenommen ein Review-Flow läuft und erreicht einen Entscheidungspunkt
    Dann wechselt der State zu "awaiting_decision"
    Und der Server sendet eine Push-Notification mit dem aktuellen Prompt und Aktionsbuttons
    Wenn der Nutzer mit "ja" antwortet
    Dann nimmt der Flow den Job wieder auf
    Und der State wechselt zurück zu "running"

  Szenario: Decision Point – Ablehnung bricht den Teilschritt ab
    Angenommen ein Review-Flow wartet auf eine Entscheidung
    Wenn der Nutzer mit "nein" antwortet
    Dann verwirft der Flow den aktuellen Teilschritt
    Und fährt mit dem nächsten Schritt fort
    Und der State ist nicht "failed"

  Szenario: PWA-Reconnect nach App-Neustart (FR-06)
    Angenommen ein Flow ist im State "awaiting_input"
    Wenn der Nutzer die PWA neustartet und GET /api/agent/flow/{session_id} aufruft
    Dann gibt der Server den aktuellen State, den aktuellen Prompt und alle bisherigen Antworten zurück
    Und der Nutzer kann den Flow nahtlos fortsetzen

  Szenario: Session-TTL abgelaufen
    Angenommen eine Flow-Session war 2 Stunden inaktiv
    Wenn der Nutzer GET /api/agent/flow/{session_id} aufruft
    Dann antwortet der Server mit HTTP 404
    Und kein Fehlercrash tritt auf

  Szenariogrundriss: Ungültiger flow_type wird abgelehnt
    Angenommen der Nutzer startet einen Flow mit flow_type "<typ>"
    Wenn der Server den Request validiert
    Dann antwortet er mit HTTP <status>

    Beispiele:
      | typ          | status |
      | new-spec     | 200    |
      | review       | 200    |
      | implement    | 200    |
      | hotfix       | 200    |
      | unknown-type | 422    |
      |              | 400    |
