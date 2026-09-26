# SPEC-0012: Seitenweise Katalogabfrage

## 1. Zweck
Die Katalog-API liefert Einträge seitenweise, damit Clients große Kataloge blättern können.

## 4. Funktionale Anforderungen

- **FR-01:** `paginate(items, page, per_page)` liefert eine `Page` mit den Einträgen der Seite `page` (1-basiert), `total` (Anzahl aller Einträge) und `total_pages`.
- **FR-02:** `per_page` liegt zwischen 1 und 100, `page` ist mindestens 1; sonst `ValueError`.
- **FR-03:** `total_pages` ist die Anzahl der Seiten, die nötig sind, um alle Einträge zu zeigen (aufgerundet); ein leerer Katalog hat 0 Seiten. Eine Seite hinter der letzten liefert eine leere Liste, keinen Fehler.
- **FR-04:** `has_next` ist genau dann wahr, wenn nach `page` noch eine Seite mit Einträgen folgt.
