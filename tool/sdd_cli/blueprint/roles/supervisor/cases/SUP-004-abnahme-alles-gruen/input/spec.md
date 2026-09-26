---
id: SPEC-0101
title: CSV-Import für Kontakte
status: in-progress
---
# SPEC-0101: CSV-Import für Kontakte

## 1. Zweck
Das Kommandozeilenwerkzeug `kontakte` soll Kontakte aus einer CSV-Datei in die bestehende
JSON-Kontaktliste (`kontakte.json`) übernehmen.

## 4. Funktionale Anforderungen
- **FR-01:** `kontakte import <datei.csv>` liest eine CSV-Datei mit Kopfzeile
  (`name;email;telefon`, Trennzeichen Semikolon, UTF-8) und liefert je Zeile einen Kontakt.
- **FR-02:** Zeilen ohne `name` oder mit einer E-Mail-Adresse ohne `@` werden übersprungen; für
  jede übersprungene Zeile wird Zeilennummer und Grund auf stderr ausgegeben.
- **FR-03:** Kontakte, deren E-Mail-Adresse (ohne Beachtung der Groß-/Kleinschreibung) bereits in
  `kontakte.json` steht, werden nicht doppelt angelegt.
- **FR-04:** Nach dem Import gibt das Werkzeug eine Zusammenfassung aus
  (`3 importiert, 1 übersprungen, 2 Duplikate`) und endet mit Exit-Code 0; ist die Datei nicht
  lesbar, endet es mit Exit-Code 2.

## 5. Nicht-Ziele
- Export nach CSV, andere Trennzeichen, Excel-Dateien.
