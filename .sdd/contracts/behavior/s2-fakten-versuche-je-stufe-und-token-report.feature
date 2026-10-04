Feature: S2-Fakten, Versuche je Stufe und Token-Report
  Als Supervisor
  möchte ich an S2 die Gründe einer Review-Ablehnung sehen und erst gefragt werden, wenn eine Stufe festhängt
  damit ich ohne Nebenkanal entscheide und die Kosten richtig einschätze

  Scenario: Review-Befunde an S2
    Given max_attempts ist 3 und das Review lehnt die Task dreimal mit einem Befund zu src/a.py Zeile 4 ab
    When die Pipeline an S2 eskaliert
    Then enthält facts.review verdict fail und den Befund mit Datei src/a.py und Zeile 4

  Scenario: Eskalation ohne Review
    Given das GREEN-Gate scheitert dreimal, ohne dass ein Review lief
    When die Pipeline an S2 eskaliert
    Then fehlt facts.review

  Scenario: Eine Review-Ablehnung führt nicht zu S2
    Given max_attempts ist 3 und das Review lehnt einmal ab
    When der Implementer danach grün liefert und das Review zustimmt
    Then gibt es keine S2-Anfrage
    And state.json zeigt stage_attempts mit review 1

  Scenario: Implementer meldet keine Änderung
    Given der Stand einer Task ist bereits grün
    When der Implementer files [] liefert
    Then wird keine Datei geschrieben
    And das Review prüft den bestehenden Stand

  Scenario: Cache-Tokens im Report
    Given ein Run, in dem der Reviewer über claude-cli 100 Input, 900 Cache-Read und 300 Cache-Write verbraucht
    When ich "sdd pipeline report" ausführe
    Then nennt der Report für reviewer Cache-Read 900 und Cache-Write 300
    And der Claude-Anteil rechnet die Cache-Tokens ein
