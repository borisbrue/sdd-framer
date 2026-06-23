Feature: Guardrail-Modul – Kommando-Semantik (sdd guard check)
  Der Guardrail blockt nur echte Gefahren, segment-genau, und unterscheidet ausführen vs. erwähnen.
  (SPEC-0051)

  # — blockierte Gefahren (unverändert ggü. bisherigem Guardrail) —
  Scenario: Force-Push auf main wird blockiert
    When "git push --force origin main" geprüft wird
    Then ist die Entscheidung "deny"

  Scenario: rm -rf auf Root wird blockiert
    When "rm -rf /" geprüft wird
    Then ist die Entscheidung "deny"

  # — behobene False Positives (Kern der Härtung) —
  Scenario: gefährliches Muster nur in einer Commit-Message erwähnt
    When "git commit -m 'beschreibt rm -rf / und $HOME'" geprüft wird
    Then ist die Entscheidung "allow"

  Scenario: f-haltiges Flag ist kein Force-Flag
    When "gh pr create --base main --body-file /tmp/x.md" geprüft wird
    Then ist die Entscheidung "allow"

  Scenario: Segment-genaue Auswertung kreuz-triggert nicht
    When "git push origin feat/x ; gh pr create --base main" geprüft wird
    Then ist die Entscheidung "allow"

  # — Alltag —
  Scenario: gezieltes Löschen im Repo
    When "rm -rf web/ui/dist" geprüft wird
    Then ist die Entscheidung "allow"

  # — sichere Degradierung —
  Scenario: Modul nicht erreichbar
    Given das Guardrail-Modul/sdd ist für den Hook nicht erreichbar
    When ein beliebiges Kommando den Hook-Wrapper durchläuft
    Then wird das Kommando erlaubt (Shell bricht nicht)
    And eine sichtbare Warnung "[WARN] Guardrail inaktiv" wird ausgegeben
