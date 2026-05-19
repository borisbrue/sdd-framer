Feature: LLM-Pool-Registry und Selector – Task-zu-LLM-Matching
  # CON-0098 | SPEC-0026

  Scenario: Low-Complexity Task geht an lokales LLM
    Given die Registry enthält "ollama/mistral" (local, cheap) und "claude-haiku" (remote, cheap)
    And ein Task mit complexity="low", context_size="S"
    When LlmSelector.select(task) aufgerufen wird
    Then wird "ollama/mistral" zurückgegeben (INV-03: lokal bevorzugt)

  Scenario: High-Complexity Task geht an powerful LLM
    Given die Registry enthält "ollama/mistral" (cheap) und "claude-opus" (powerful)
    And ein Task mit complexity="high", context_size="L"
    When LlmSelector.select(task) aufgerufen wird
    Then wird "claude-opus" zurückgegeben

  Scenario: Fallback wenn bevorzugtes Tier fehlt
    Given die Registry enthält nur "claude-haiku" (cheap)
    And ein Task mit complexity="high", context_size="L"
    When LlmSelector.select(task) aufgerufen wird
    Then wird "claude-haiku" als Fallback zurückgegeben

  Scenario: Kontext-Limit-Verletzung
    Given "ollama/mistral" hat max_context_tokens=4096
    And ein Task mit estimated_tokens=8000
    When LlmSelector.select(task) aufgerufen wird
    Then wird "ollama/mistral" nicht ausgewählt (INV-02)

  Scenario: Leere Registry
    Given die Registry ist leer
    When LlmSelector.select(task) aufgerufen wird
    Then wird LlmUnavailableError geworfen

  Scenario: Doppelte LLM-ID ist unzulässig
    Given ein LLM "llm-1" bereits in der Registry
    When ein zweiter Eintrag mit id="llm-1" registriert wird
    Then wird ValueError mit "Doppelte" geworfen
