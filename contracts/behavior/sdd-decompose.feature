Feature: sdd decompose – Task-Ableitung und Klassifizierung aus Spec
  # CON-0097 | SPEC-0026

  Scenario: Erfolgreiche Dekomposition mit Bestätigung
    Given ein valides Spec "SPEC-0026" mit 16 FRs
    When ich "sdd decompose SPEC-0026" ausführe
    Then erhalte ich eine Task-Liste mit mindestens 5 Tasks
    And jeder Task hat complexity, context_size und type gesetzt
    When ich die Liste mit "ja" bestätige
    Then werden die Tasks als JSON in ".sdd/tasks/SPEC-0026.json" gespeichert

  Scenario: Entwickler bearbeitet Task vor Bestätigung
    Given eine generierte Task-Liste für SPEC-0026
    When ich Task 3 mit neuem Titel editiere
    Then spiegelt die gespeicherte Liste den aktualisierten Titel wider

  Scenario: Leere Spec liefert Fehler
    Given ein Spec ohne Funktionale Anforderungen
    When ich "sdd decompose SPEC-XXXX" ausführe
    Then erhalte ich Exit-Code 1 und Meldung "Keine Tasks ableitbar"

  Scenario: Doppelter Task-Titel ist unzulässig
    Given ein LLM-Ergebnis mit zwei Tasks mit identischem Titel "Implementiere X"
    When TaskDecomposer die Liste validiert
    Then wird ValueError mit "Doppelter" geworfen

  Scenario: estimated_tokens ist immer positiv
    Given eine Task-Liste mit N Tasks
    When jeder Task geprüft wird
    Then ist estimated_tokens > 0 für alle Tasks
