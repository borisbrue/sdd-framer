# CON-0207 · SPEC-0060 FR-01..FR-10
Feature: Usage-Erfassung
  Als Nutzer von sdd-framer
  möchte ich für jeden LLM-Aufruf verlässliche Tokenzahlen inklusive Reasoning-Tokens
  um Kosten, Modelle und Rollen vergleichen zu können, auch im keyfreien Betrieb

  Scenario: claude-cli liest die Usage aus dem Envelope
    Given claude --print liefert ein Envelope mit input_tokens 1200, output_tokens 300, cache_read_input_tokens 50, cache_creation_input_tokens 70, thinking_tokens 40, stop_reason end_turn und Modell claude-opus-5-5
    When ein Aufruf über den claude-cli-Provider erfolgt
    Then hat die Usage input_tokens 1200, output_tokens 300, cache_read_tokens 50, cache_creation_tokens 70, reasoning_tokens 40, finish_reason end_turn, server_model claude-opus-5-5 und source reported

  Scenario: claude-cli ohne Usage im Envelope
    Given claude --print liefert ein Envelope nur mit result
    When ein Aufruf über den claude-cli-Provider erfolgt
    Then liefert der Aufruf den Text aus result
    And die Usage hat source unavailable

  Scenario: openai-compat mit Reasoning-Tokens
    Given der Server meldet completion_tokens_details.reasoning_tokens 800 und finish_reason length
    When ein Aufruf über den openai-compat-Provider erfolgt
    Then hat die Usage reasoning_tokens 800, finish_reason length, server_model und source reported

  Scenario: openai-compat ohne Usage-Block
    Given der Server antwortet ohne usage
    When ein Aufruf über den openai-compat-Provider erfolgt
    Then hat die Usage source unavailable

  Scenario: CodeGen liefert Usage und bleibt kompatibel
    When ein CodeGen-Provider aus der Factory generate aufruft
    Then enthält das Ergebnis Dateien, Erklärung und Usage
    And das Ergebnis lässt sich wie bisher als (files, explanation) entpacken

  Scenario Outline: Jede Factory-Komponente wird erfasst
    Given eine Fake-Senke ist registriert
    When die Komponente <komponente> einmal aufgerufen wird
    Then erhält die Senke genau einen Datensatz mit component <komponente>

    Examples:
      | komponente   |
      | completion   |
      | evaluator    |
      | analyzer     |
      | ai_routes    |
      | local_llm    |
      | orchestrator |

  Scenario: Aufruf mit Ausnahme
    Given der Provider wirft beim Aufruf eine Ausnahme
    When ein Aufruf erfolgt
    Then erhält die Senke einen Datensatz mit finish_reason error und source unavailable
    And die Ausnahme wird unverändert weitergegeben

  Scenario: Aufrufkontext
    Given ein Aufruf innerhalb von usage_context(spec_id="SPEC-0900", run_id="r1", role="implementer")
    And darin verschachtelt usage_context(attempt=2)
    Then hat der Datensatz spec_id SPEC-0900 und run_id r1
    And context_json enthält role implementer und attempt 2

  Scenario: Ohne Kontext
    When ein Aufruf ohne usage_context erfolgt
    Then hat der Datensatz spec_id, run_id und context_json leer

  Scenario: Senkenfehler
    Given eine Senke wirft beim Schreiben einen Fehler und eine zweite Senke ist registriert
    When ein Aufruf erfolgt
    Then liefert der Aufruf sein Ergebnis
    And die zweite Senke erhält den Datensatz
    And ein Warnhinweis wird geloggt

  Scenario: decompose und Analyzer laufen über die Factory
    When sdd decompose und der Analyzer der Web-API je einen LLM-Aufruf machen
    Then erzeugt jeder Aufruf genau einen Datensatz

  Scenario: Web-API schreibt und liest token_usage
    Given .sdd/ai_usage.json enthält zwei Altdatensätze
    When ich "sdd upgrade" ausführe
    Then enthält token_usage beide Datensätze mit context_json origin web
    And die Usage-Route der Web-API liefert Summe und Liste aus token_usage

  Scenario: token-history zeigt Reasoning-Tokens
    Given token_usage enthält einen Datensatz mit reasoning_tokens 40
    When ich "sdd token-history --export out.csv" ausführe
    Then enthält out.csv die Spalten reasoning_tokens, finish_reason, source, run_id und context_json

  Scenario: Migration bestehender Datenbanken
    Given eine evaluations.db mit token_usage im alten Schema und einer Zeile
    When die SQLite-Senke den ersten Datensatz schreibt
    Then existieren die neuen Spalten
    And die alte Zeile ist unverändert und bleibt schema-gültig
