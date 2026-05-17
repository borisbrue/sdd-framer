Feature: Execution Gate – Phase State Machine

  Background:
    Given das SDD-CLI ist installiert
    And eine Spec-Datei für "SPEC-0014" existiert mit status "approved"

  # ── Execute Gate ────────────────────────────────────────────────────────────

  Scenario: Execute blockiert wenn pipeline_phase nicht execute-unlocked
    Given SPEC-0014 hat pipeline_phase "contracts-review"
    When "sdd execute SPEC-0014" ausgeführt wird
    Then ist der Exit-Code 2
    And der Output enthält "Execution Gate nicht bestanden"
    And der Output enthält eine Phasen-Statusübersicht

  Scenario: Execute freigegeben wenn alle Phasen grün
    Given SPEC-0014 hat pipeline_phase "execute-unlocked"
    And keine Konflikte für SPEC-0014 haben status "open"
    When "sdd execute SPEC-0014" ausgeführt wird
    Then ist der Exit-Code 0
    And die Orchestrator-Pipeline wird gestartet

  Scenario: Force ohne override-reason wird abgelehnt
    Given SPEC-0014 hat pipeline_phase "contracts-review"
    When "sdd execute SPEC-0014 --force" ohne --override-reason ausgeführt wird
    Then ist der Exit-Code 1
    And der Output enthält "--override-reason ist erforderlich"

  Scenario: Force mit override-reason wird akzeptiert und protokolliert
    Given SPEC-0014 hat pipeline_phase "contracts-review"
    When "sdd execute SPEC-0014 --force --override-reason 'Hotfix'" ausgeführt wird
    Then ist der Exit-Code 0
    And das Pipeline-JSON enthält ein override-Objekt
    And override.reason ist "Hotfix"
    And override.triggered_at ist gesetzt

  # ── Phasenübergänge ─────────────────────────────────────────────────────────

  Scenario: Phase 2 blockiert wenn Phase 1 Pflichtfelder fehlen
    Given SPEC-0014 hat kein "owner"-Feld im Frontmatter
    When "sdd spec review SPEC-0014" ausgeführt wird
    Then ist der Exit-Code 1
    And der Output enthält "Pflichtfeld fehlt: owner"

  Scenario: Phase 4 blockiert wenn Phase 3 nicht abgeschlossen
    Given SPEC-0014 hat pipeline_phase "spec-review"
    When "sdd contract review SPEC-0014" ausgeführt wird
    Then ist der Exit-Code 2
    And der Output enthält "Phase 3 (contracts-proposed) noch nicht abgeschlossen"

  Scenario: Phase kann wiederholt werden ohne vorherige Phasen neu zu starten
    Given SPEC-0014 hat pipeline_phase "contracts-review"
    And Phase 5 hat result "failed"
    When "sdd contract review SPEC-0014" erneut ausgeführt wird
    Then startet Phase 5 neu ohne Phase 1–4 zu wiederholen
    And phase_history behält die alten Phase 1–4 Einträge

  # ── Persistenz ──────────────────────────────────────────────────────────────

  Scenario: Phasenstatus wird nach jedem Abschluss sofort persistiert
    Given Phase 3 wird gerade ausgeführt
    When der Prozess während Phase 3 unerwartet beendet wird
    Then enthält das Pipeline-JSON noch die Phasen 1 und 2 mit result "ok"
    And pipeline_phase ist "spec-review" (letzte erfolgreich abgeschlossene Phase)
