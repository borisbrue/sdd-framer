# CON-0020: Execute Flow – UI-Verhalten und Status-Übergänge
# Spec: SPEC-0007

Feature: Execute Flow – UI-Verhalten und Status-Übergänge

  Background:
    Given die SDD Web UI ist geöffnet und eine Spec ist geladen

  # ─── INV-01: Execute-Button nur bei approved ─────────────────────────────

  Scenario Outline: Execute-Button Sichtbarkeit nach Status
    Given eine Spec mit status "<status>"
    When ich die SpecDetail-Ansicht öffne
    Then ist der Execute-Button <sichtbarkeit>

    Examples:
      | status      | sichtbarkeit              |
      | draft       | nicht sichtbar            |
      | review      | nicht sichtbar            |
      | approved    | sichtbar und aktiv        |
      | implemented | nicht sichtbar            |
      | deprecated  | nicht sichtbar            |

  # ─── INV-02: Kein Doppel-Start ───────────────────────────────────────────

  Scenario: Execute-Button deaktiviert während Pipeline läuft
    Given eine Spec mit status "approved"
    And GET /api/pipeline/active gibt einen laufenden Run zurück
    When ich die SpecDetail-Ansicht öffne
    Then ist der Execute-Button sichtbar aber deaktiviert
    And zeigt der Button einen Lade-Indikator

  # ─── INV-03: Status-Auto-Transition nach Erfolg ──────────────────────────

  Scenario: Spec-Status wechselt nach erfolgreichem Pipeline-Lauf
    Given eine Spec mit status "approved"
    And der Pipeline-Lauf endet mit final_status "labeled"
    When die Status-Transition abgeschlossen ist
    Then hat die Spec-Datei auf dem Dateisystem status "implemented"
    And zeigt die SpecDetail-Ansicht status "implemented"

  Scenario: Spec-Status wechselt nach gemergtem Pipeline-Lauf
    Given eine Spec mit status "approved"
    And der Pipeline-Lauf endet mit final_status "merged"
    When die Status-Transition abgeschlossen ist
    Then hat die Spec-Datei auf dem Dateisystem status "implemented"

  # ─── INV-04: Kein Status-Update nach Fehlschlag ──────────────────────────

  Scenario: Spec-Status bleibt approved nach fehlgeschlagenem Lauf
    Given eine Spec mit status "approved"
    And der Pipeline-Lauf endet mit final_status "failed"
    When der Fehlschlag registriert ist
    Then hat die Spec-Datei auf dem Dateisystem weiterhin status "approved"

  # ─── INV-05: 422 bei nicht-approved Spec ─────────────────────────────────

  Scenario: API lehnt nicht-approved Spec ab
    Given eine Spec mit status "implemented"
    When POST /api/orchestrate mit dieser Spec-ID aufgerufen wird
    Then antwortet der Endpoint mit HTTP 422
    And enthält die Fehlermeldung "approved"

  # ─── INV-06: Polling stoppt nach Endzustand ──────────────────────────────

  Scenario Outline: Polling stoppt bei Endzustand
    Given ein laufender Pipeline-Lauf im Status-Panel
    And GET /api/pipeline/{run_id} gibt status "<endzustand>" zurück
    When der Client den Poll-Response empfängt
    Then sendet der Client keine weiteren Polling-Requests
    And wird das Status-Panel in den Endzustand "<endzustand>" versetzt

    Examples:
      | endzustand |
      | labeled    |
      | merged     |
      | failed     |
      | dry_run    |

  # ─── Reload-Recovery (SPEC-0007 §4.2) ───────────────────────────────────

  Scenario: Status-Panel wird nach Seiten-Reload wiederhergestellt
    Given ein laufender Pipeline-Lauf mit run_id gespeichert in sessionStorage
    When der User die Seite neu lädt
    Then ruft SpecDetail GET /api/pipeline/{run_id} auf
    And zeigt das Status-Panel den aktuellen Fortschritt

  Scenario: Fallback auf active-Run-Endpoint wenn sessionStorage leer
    Given kein run_id in sessionStorage für diese Spec
    And GET /api/pipeline/active gibt einen laufenden Run zurück
    When SpecDetail geladen wird
    Then wird der Run aus dem active-Endpoint wiederhergestellt
    And startet das Polling für diesen Run
