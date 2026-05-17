Feature: Contract Conflict Detection – Analyse-Verhalten

  Background:
    Given das SDD-CLI ist installiert
    And SPEC-0014 hat pipeline_phase "contracts-draft"
    And der Workspace enthält aktive Contracts

  # ── Konflikt-Erkennung ──────────────────────────────────────────────────────

  Scenario: endpoint-overlap wird erkannt
    Given CON-0027 definiert "POST /api/gate/{spec_id}/approve"
    And CON-0014 definiert ebenfalls "POST /api/docs/{id}/analyze" (anderer Pfad, kein Overlap)
    And ein fiktiver CON-XXXX definiert "POST /api/gate/{spec_id}/approve"
    When "sdd contract review SPEC-0014" ausgeführt wird
    Then enthält der Konfliktbericht einen Eintrag mit type "endpoint-overlap"
    And conflicting_contract ist "CON-XXXX"
    And severity ist "high"

  Scenario: behavior-contradiction zwischen zwei Gherkin-Contracts
    Given CON-0025 definiert Scenario "Execute erlaubt wenn status=approved UND phase=execute-unlocked"
    And CON-0020 definiert Invariante "Execute-Gate = status == approved" (ohne phase-Bedingung)
    When "sdd contract review SPEC-0014" ausgeführt wird
    Then enthält der Konfliktbericht einen Eintrag mit type "scope-overlap"
    And new_contract ist "CON-0025"
    And conflicting_contract ist "CON-0020"

  Scenario: Kein Konflikt wenn Contracts disjunkte Bereiche abdecken
    Given alle neuen Contracts von SPEC-0014 haben eindeutige Endpunkte und Szenarien
    When "sdd contract review SPEC-0014" ausgeführt wird
    Then enthält der Konfliktbericht 0 Konflikte
    And pipeline_phase wechselt zu "contracts-review" mit result "ok"

  # ── Konflikt-Auflösung ──────────────────────────────────────────────────────

  Scenario: Phase 5 blockiert solange offene Konflikte existieren
    Given Konflikt "CF-0014-001" hat status "open"
    When "sdd test generate SPEC-0014" ausgeführt wird
    Then ist der Exit-Code 2
    And der Output enthält "CF-0014-001 ist noch offen"
    And der Output enthält "sdd conflict resolve" oder "sdd conflict acknowledge"

  Scenario: Konflikt auflösen setzt status auf resolved
    Given Konflikt "CF-0014-001" hat status "open"
    When "sdd conflict resolve CF-0014-001 --action extend --spec SPEC-0014" ausgeführt wird
    Then hat CF-0014-001 status "resolved"
    And resolution.action ist "extend"

  Scenario: Acknowledge ohne reason wird abgelehnt
    Given Konflikt "CF-0014-001" hat status "open"
    When "sdd conflict acknowledge CF-0014-001 --spec SPEC-0014" ohne --reason ausgeführt wird
    Then ist der Exit-Code 1
    And der Output enthält "--reason ist erforderlich"

  Scenario: Alle Konflikte resolved – Phase 5 wird bestanden
    Given alle Konflikte von SPEC-0014 haben status "resolved" oder "acknowledged"
    When Phase 5 erneut geprüft wird
    Then pipeline_phase wechselt zu "contracts-review" mit result "ok"

  # ── Performance & Caching ───────────────────────────────────────────────────

  Scenario: Workspace-Scan dauert unter 30 Sekunden bei 50 Contracts
    Given der Workspace enthält 50 Contract-Dateien mit status active oder draft
    When "sdd contract review SPEC-0014" ausgeführt wird
    Then ist die Analyse in weniger als 30 Sekunden abgeschlossen

  Scenario: Cache wird nach Contract-Änderung invalidiert
    Given der Workspace-Cache ist für Contract CON-0020 gespeichert
    And CON-0020 wird inhaltlich geändert (Datei-Hash ändert sich)
    When die nächste Analyse für eine beliebige SPEC ausgeführt wird
    Then wird CON-0020 neu aus der Datei gelesen (Cache-Miss)
