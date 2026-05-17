Feature: Auto Test Generation – Verhalten

  Background:
    Given das SDD-CLI ist installiert
    And SPEC-0014 hat pipeline_phase "contracts-review" mit result "ok"
    And alle Konflikte von SPEC-0014 sind resolved oder acknowledged

  # ── Basis-Generierung ───────────────────────────────────────────────────────

  Scenario: Gherkin-Contract erzeugt pytest-bdd Testdatei
    Given CON-0025 ist ein gherkin-Contract mit 4 Scenarios
    When "sdd test generate SPEC-0014" ausgeführt wird
    Then existiert "tests/behavior/test_con-0025.py"
    And die Datei enthält mindestens 4 Testfunktionen
    And die erste Zeile ist "# AUTO-GENERATED from CON-0025 via sdd test generate — do not delete"

  Scenario: OpenAPI-Contract erzeugt httpx-Testdatei
    Given CON-0027 ist ein openapi-Contract mit 8 Endpunkten
    When "sdd test generate SPEC-0014" ausgeführt wird
    Then existiert "tests/api/test_con-0027.py"
    And jeder Endpunkt hat mindestens einen Happy-Path-Test

  Scenario: JSON-Schema-Contract erzeugt jsonschema-Testdatei
    Given CON-0029 ist ein json-schema-Contract
    When "sdd test generate SPEC-0014" ausgeführt wird
    Then existiert "tests/data/test_con-0029.py"
    And die Datei enthält Tests für gültige und ungültige Schema-Instanzen

  Scenario: Generierte Tests sind syntaktisch valide
    When "sdd test generate SPEC-0014" ausgeführt wird
    Then läuft "pytest --collect-only tests/" ohne SyntaxError
    And läuft ohne ImportError

  # ── Qualitätskriterien ──────────────────────────────────────────────────────

  Scenario: Jedes Gherkin-Scenario hat mindestens einen Test
    Given CON-0025.feature enthält 7 Scenarios
    When "sdd test generate SPEC-0014" ausgeführt wird
    Then enthält tests/behavior/test_con-0025.py mindestens 7 Testfunktionen

  Scenario: Error-Cases aus Gherkin werden abgedeckt
    Given CON-0025.feature enthält ein Scenario "Force ohne override-reason wird abgelehnt"
    When "sdd test generate SPEC-0014" ausgeführt wird
    Then enthält test_con-0025.py eine Testfunktion die Exit-Code 1 prüft

  # ── Re-Run-Verhalten ────────────────────────────────────────────────────────

  Scenario: Manuell erweiterter Test wird nicht überschrieben
    Given tests/behavior/test_con-0025.py existiert bereits
    And die Datei enthält eine manuell hinzugefügte Funktion "test_custom_case"
    When "sdd test generate SPEC-0014" erneut ausgeführt wird
    Then bleibt "test_custom_case" in der Datei erhalten

  Scenario: Phase 6 blockiert wenn pytest dry-run fehlschlägt
    Given ein generierter Test hat einen SyntaxError
    When "sdd test generate SPEC-0014" ausgeführt wird
    Then ist der Exit-Code 1
    And der Output enthält den SyntaxError mit Dateiname und Zeilennummer
    And pipeline_phase bleibt auf "contracts-review"
