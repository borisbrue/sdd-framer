# SPEC-0007: Benutzerimport aus CSV

## 1. Zweck
Administratoren legen Benutzer gesammelt über eine CSV-Datei an.

## 4. Funktionale Anforderungen

- **FR-01:** Die CSV-Datei hat die Kopfzeile `email,name,role`; jede weitere Zeile beschreibt einen Benutzer.
- **FR-02:** E-Mail-Adressen werden getrimmt und kleingeschrieben. Eine Adresse, die (nach Normalisierung) schon importiert wurde, wird übersprungen und in `skipped_duplicates` gezählt.
- **FR-03:** Zeilen mit leerer oder ungültiger E-Mail (kein `@`) oder mit einer Rolle außerhalb von `admin`, `editor`, `viewer` werden nicht importiert. Der Bericht führt sie in `errors` mit Zeilennummer (Kopfzeile = Zeile 1) und Grund.
- **FR-04:** Eine leere Rolle wird zu `viewer`.

## 5. Nicht-Ziele
- Kein Schreiben in die Datenbank; `import_rows` liefert nur den Bericht.
