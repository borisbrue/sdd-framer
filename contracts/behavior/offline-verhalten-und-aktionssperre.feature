# language: de
Funktionalität: Offline-Verhalten und Aktionssperre der PWA

  Als Nutzer der PWA
  möchte ich immer den aktuellen oder zuletzt bekannten Projektstatus sehen
  und keine Aktionen ausführen können, wenn der Hub nicht erreichbar ist,
  damit keine unkontrollierten oder verzögerten Steuerbefehle entstehen.

  Hintergrund:
    Angenommen die PWA ist geöffnet und zeigt die Projektliste an

  Szenario: Start- und Stopp-Schaltflächen sind gesperrt, wenn der Hub nicht erreichbar ist
    Angenommen der Hub ist nicht erreichbar
    Und die Projektliste enthält mindestens ein Projekt mit Status "stopped" und eines mit Status "running"
    Wenn der Nutzer die Projektliste betrachtet
    Dann sind alle Start-Schaltflächen deaktiviert und nicht interaktiv
    Und alle Stopp-Schaltflächen sind deaktiviert und nicht interaktiv
    Und es werden keine Aktionen zwischengespeichert oder verzögert ausgeführt

  Szenario: Offline-Hinweis und letzter bekannter Status werden bei Verbindungsverlust angezeigt
    Angenommen der Hub war erreichbar und die PWA hat den Projektstatus zuletzt um 14:00 Uhr erfolgreich abgerufen
    Wenn der Hub anschließend nicht mehr erreichbar ist
    Dann zeigt die PWA den Projektstatus vom letzten erfolgreichen Abruf an
    Und ein klar sichtbarer Offline-Hinweis wird eingeblendet
    Und der Zeitstempel des letzten erfolgreichen Abrufs ist im Offline-Hinweis sichtbar

  Szenario: Aktionssperre wird aufgehoben, wenn der Hub wieder erreichbar wird
    Angenommen der Hub war nicht erreichbar und die PWA befindet sich im Offline-Modus
    Wenn der Hub wieder erreichbar wird
    Dann wechselt die PWA automatisch in den Online-Modus
    Und die Start- und Stopp-Schaltflächen werden wieder aktiviert
    Und der Offline-Hinweis wird ausgeblendet
    Und die PWA ruft den aktuellen Projektstatus vom Hub ab

  Szenario: Heartbeat-Mechanismus erkennt Verbindungsverlust aktiv
    Angenommen die PWA überwacht aktiv die Erreichbarkeit des Hubs per Heartbeat
    Wenn der Hub nicht mehr auf Heartbeat-Anfragen antwortet
    Dann erkennt die PWA den Verbindungsverlust ohne Nutzerinteraktion
    Und schaltet selbstständig in den Offline-Modus
    Und deaktiviert alle Steuer-Schaltflächen in der Projektliste

  Szenario: Steueraktion wird nur im Online-Modus an den Hub übermittelt
    Angenommen der Hub ist erreichbar
    Und ein Projekt hat den Status "stopped"
    Wenn der Nutzer die Start-Schaltfläche für dieses Projekt betätigt
    Dann wird eine Start-Anfrage an die Hub-API übermittelt
    Und der angezeigte Status des Projekts ändert sich innerhalb von 5 Sekunden sichtbar
    Und es findet kein vollständiger Seitenneuladung statt

  Szenario: Kein API-Aufruf wird im Offline-Modus ausgelöst
    Angenommen der Hub ist nicht erreichbar
    Und ein Projekt hat den Status "running" gemäß des zuletzt bekannten Zustands
    Wenn der Nutzer versucht, die Stopp-Schaltfläche zu betätigen
    Dann wird kein API-Aufruf an den Hub gesendet
    Und der angezeigte Status des Projekts bleibt unverändert
    Und die Schaltfläche reagiert nicht auf die Interaktion
