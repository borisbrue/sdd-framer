---
id: SPEC-0021
title: Kundenimport aus CSV
status: approved
---

# SPEC-0021: Kundenimport aus CSV

## 1. Kontext

Der Vertrieb pflegt Kundenlisten in Tabellenkalkulationen und exportiert sie als CSV. Bisher
werden sie von Hand in die Datenbank `crm.sqlite` übertragen. Das Kommando
`python3 -m crm.importer kunden.csv` soll das übernehmen. Die Tabelle `customers`
(`id`, `email` UNIQUE, `name`, `country`, `created_at`) existiert bereits und wird von
`crm/db.py` verwaltet.

Erwartete Spalten (Kopfzeile, Reihenfolge beliebig): `email`, `name`, `country`.
Zusätzliche Spalten werden ignoriert.

## 2. Funktionale Anforderungen

- **FR-01:** Der Importer liest die Datei als UTF-8 und akzeptiert ein vorangestelltes BOM.
  Als Trennzeichen werden Komma und Semikolon erkannt (anhand der Kopfzeile). Fehlt eine der
  erwarteten Spalten, bricht der Import vor jeder Zeilenprüfung mit einer Meldung ab, die die
  fehlenden Spalten nennt.
- **FR-02:** Jede Datenzeile wird geprüft: `email` enthält genau ein `@` und einen Punkt im
  Domainteil; `name` ist nach Entfernen von Leerraum an den Rändern nicht leer; `country` ist
  ein zweibuchstabiger ISO-3166-Code in Großbuchstaben aus der Liste in `crm/countries.py`.
- **FR-03:** Alle Fehler werden gesammelt, nicht beim ersten abgebrochen. Der Fehlerbericht
  nennt je Fehler die Zeilennummer in der Datei (Kopfzeile = Zeile 1), die Spalte und den
  Grund, sortiert nach Zeilennummer.
- **FR-04:** Der Import ist alles oder nichts: Enthält die Datei mindestens einen Fehler, wird
  keine Zeile geschrieben. Sonst werden alle Zeilen in einer einzigen Transaktion eingefügt;
  bricht das Einfügen ab, bleibt die Datenbank unverändert.
- **FR-05:** Mit `--dry-run` wird vollständig geprüft und der Bericht ausgegeben, aber nie
  geschrieben. Die Ausgabe endet mit `N Zeilen gültig, M Fehler`.
- **FR-06:** Eine E-Mail-Adresse (Vergleich ohne Groß-/Kleinschreibung) darf weder zweimal in
  der Datei noch bereits in `customers` vorkommen. Jede Dublette ist ein Fehler im Sinne von
  FR-03 und nennt bei Dubletten innerhalb der Datei die Zeile des ersten Vorkommens.

## 3. Nicht-Ziele

- Kein Import aus `.xlsx` oder anderen Formaten als CSV.
- Keine automatische Korrektur von Daten (z. B. Ländernamen in Codes umwandeln).
- Kein Aktualisieren bestehender Kunden (Upsert).
