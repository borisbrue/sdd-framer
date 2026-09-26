# SPEC-0021: Suche über Notizen

## 1. Zweck
Nutzer durchsuchen die Titel ihrer eigenen Notizen. Suchtext, Sortierung und Limit kommen aus Query-Parametern.

## 4. Funktionale Anforderungen

- **FR-01:** `search_notes(conn, owner_id, text)` liefert die Notizen des Besitzers, deren Titel `text` enthält; Groß-/Kleinschreibung spielt (für ASCII) keine Rolle. Notizen anderer Besitzer erscheinen nie.
- **FR-02:** `sort` ist `updated` (neueste zuerst, Standard) oder `title` (alphabetisch, ohne Beachtung der Schreibung); jeder andere Wert führt zu `ValueError`.
- **FR-03:** `limit` ist standardmäßig 20; Werte über 50 werden auf 50 begrenzt, Werte unter 1 führen zu `ValueError`.
- **FR-04:** `%` und `_` im Suchtext werden wörtlich gesucht, nicht als Platzhalter.
