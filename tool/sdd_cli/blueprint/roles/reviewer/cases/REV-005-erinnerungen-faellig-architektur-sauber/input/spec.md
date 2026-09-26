# SPEC-0031: Erinnerungen

## 1. Zweck
Ein kleines Kommandozeilenwerkzeug verwaltet Erinnerungen in einer JSON-Datei.

## 4. Funktionale Anforderungen

- **FR-01:** `reminders list` zeigt alle Erinnerungen, eine je Zeile im Format `YYYY-MM-DD HH:MM  <Text>`.
- **FR-02:** Eine Erinnerung ist fällig, wenn sie nicht erledigt ist und `due_at` kleiner oder gleich dem aktuellen Zeitpunkt (UTC) ist. `due_reminders` liefert die fälligen Erinnerungen, älteste zuerst.
- **FR-03:** `reminders due` gibt die fälligen Erinnerungen im Format von FR-01 aus; gibt es keine, bleibt die Ausgabe leer. Exit-Code 0.
- **FR-04:** Ist die Datei nicht lesbar, meldet das Werkzeug den Fehler auf stderr und endet mit Exit-Code 2.
