# language: de
Funktionalität: Holdout-Status im ContainerView
  Als Entwickler
  möchte ich den Holdout-Status im ContainerView sehen
  um sofort zu wissen, ob eine Evaluierung läuft oder abgeschlossen ist

  Grundlage:
    Angenommen der SDD Hub ist geöffnet
    Und der Nutzer betrachtet den ContainerView für "SPEC-0043"

  Szenario: Laufender Holdout wird angezeigt
    Angenommen ein Holdout-Lauf für "SPEC-0043" ist aktiv
    Wenn der ContainerView geladen wird
    Dann zeigt der Status-Badge den Text "running"
    Und der Badge enthält ein visuelles Lauf-Indikator-Element

  Szenario: Badge aktualisiert sich automatisch via SSE
    Angenommen ein Holdout-Lauf für "SPEC-0043" wechselt von "running" zu "passed"
    Wenn das SSE-Event empfangen wird
    Dann aktualisiert sich der Status-Badge ohne Seiten-Reload auf "passed"

  Szenario: Bestandener Holdout
    Angenommen ein Holdout-Lauf für "SPEC-0043" hat alle Szenarien bestanden
    Wenn der ContainerView geladen wird
    Dann zeigt der Status-Badge den Text "passed"
    Und keine Szenario-Detail-Liste ist sichtbar

  Szenario: Fehlgeschlagener Holdout mit Szenario-Details
    Angenommen ein Holdout-Lauf für "SPEC-0043" hat Szenario "Login" nicht bestanden
    Wenn der ContainerView geladen wird
    Dann zeigt der Status-Badge den Text "failed"
    Und die aufklappbare Detail-Liste enthält einen Eintrag "Login"

  Szenario: Kein Holdout vorhanden
    Angenommen kein Holdout-Lauf existiert für "SPEC-0043"
    Wenn der ContainerView geladen wird
    Dann zeigt der Status-Badge keinen aktiven Status (neutral / leer)
    Und keine Szenario-Detail-Liste ist sichtbar

  Szenario: SSE-Verbindung bricht ab
    Angenommen der SSE-Stream für "SPEC-0043" ist unterbrochen
    Wenn die Verbindung abbricht
    Dann zeigt der Status-Badge den Text "unknown"
    Und das Frontend versucht die SSE-Verbindung mit Backoff neu aufzubauen

  Szenario: Nur der neueste Holdout-Lauf wird angezeigt (INV-02)
    Angenommen zwei Holdout-Läufe für "SPEC-0043" existieren
    Und der neuere Lauf hat Status "passed"
    Und der ältere Lauf hat Status "failed"
    Wenn der ContainerView geladen wird
    Dann zeigt der Status-Badge den Text "passed"

  Szenario: Keine Trigger-Aktionen im ContainerView sichtbar (INV-03)
    Angenommen ein Holdout-Lauf für "SPEC-0043" hat Status "failed"
    Wenn der ContainerView geladen wird
    Dann enthält der ContainerView keinen "Holdout starten"-Button
    Und enthält der ContainerView keine Konfigurations-Elemente für Holdout-Parameter

  Szenariogrundriss: Badge-Text entspricht dem API-Status
    Angenommen der API-Status für "SPEC-0043" ist "<api_status>"
    Wenn der ContainerView geladen wird
    Dann zeigt der Status-Badge den Text "<badge_text>"

    Beispiele:
      | api_status | badge_text |
      | running    | running    |
      | passed     | passed     |
      | failed     | failed     |
      | none       |            |
