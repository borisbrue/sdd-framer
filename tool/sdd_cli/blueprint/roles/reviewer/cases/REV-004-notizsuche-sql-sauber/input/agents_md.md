# AGENTS.md

## Architektur
- `notes/schema.py`: Schema und Verbindung, `notes/models.py`: Datenklassen, `notes/repository.py`: alle SQL-Abfragen.
- Nur Standardbibliothek (`sqlite3`), kein ORM.

## Regeln
- Nutzereingaben gelangen nur als gebundene Parameter (`?`) in SQL. Bezeichner, die sich nicht binden lassen (Spalten, Sortierrichtung), kommen ausschließlich aus festen Zuordnungen im Code.
- Fehlerhafte Eingaben werden mit `ValueError` abgelehnt; die HTTP-Schicht übersetzt das in 400.
- Tests laufen gegen eine echte In-Memory-SQLite-Datenbank, keine Mocks für `sqlite3`.
