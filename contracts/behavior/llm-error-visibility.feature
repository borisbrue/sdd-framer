Feature: Sichtbare LLM-Fehler in SOLID-Check und Pattern-Vorschlägen
  Ein LLM-Infrastruktur-Fehler wird sichtbar gemeldet, statt als leeres/"sauberes" Ergebnis
  getarnt zu werden. (SPEC-0050)

  Scenario: Pattern-Suggest meldet LLM-Fehler statt leerer Vorschlagsliste
    Given der completion-Provider ist nicht nutzbar (z. B. claude CLI fehlt)
    When der Pattern-Vorschlag für ein Artefakt ausgeführt wird
    Then erscheint eine sichtbare Warnung "[WARN] Pattern-Vorschläge übersprungen: <Grund>"
    And das Ergebnis wird NICHT als "Keine Pattern-Vorschläge generiert" dargestellt

  Scenario: SOLID-Check meldet LLM-Fehler statt "compliant"
    Given der completion-Provider ist nicht nutzbar
    When der LLM-gestützte SOLID-Check ausgeführt wird
    Then erscheint eine sichtbare Warnung über den LLM-Fehler
    And das Ergebnis wird NICHT als "compliant" dargestellt

  Scenario: Bei funktionierendem Provider bleibt das Verhalten unverändert
    Given ein nutzbarer claude-cli-Provider
    When Pattern-Suggest bzw. SOLID-Check ausgeführt wird
    Then werden echte Vorschläge bzw. echte SOLID-Befunde zurückgegeben
