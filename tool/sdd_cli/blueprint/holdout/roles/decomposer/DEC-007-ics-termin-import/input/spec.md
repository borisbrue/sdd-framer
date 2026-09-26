---
id: SPEC-0031
title: "ICS-Import für die Raumbelegung"
status: approved
---

# SPEC-0031: ICS-Import für die Raumbelegung

## 1. Kontext

Die Raumbelegung der Volkshochschule liegt in einer SQLite-Datenbank (`belegung.db`). Dozenten
schicken ihre Kurstermine als `.ics`-Export aus ihrem Kalender. Bisher tippt das Sekretariat die
Termine ab. Ein Kommandozeilen-Import `belegung import <datei.ics> --raum <raum-id>` soll das
ersetzen.

## 2. Nicht-Ziele

- Kein Export nach ICS.
- Wiederholungsregeln außer `FREQ=WEEKLY` (täglich, monatlich, jährlich, `BYSETPOS` …) werden
  nicht unterstützt; solche Termine werden als Fehler gemeldet, nicht importiert.
- Keine Konflikterkennung zwischen Terminen (ist SPEC-0032).
- Keine Web-Oberfläche.

## 3. Datenmodell

Neue Tabelle `termin(uid TEXT, beginn_utc TEXT, ende_utc TEXT, raum_id TEXT, titel TEXT,
quelle TEXT, PRIMARY KEY (uid, beginn_utc))`. Die Tabelle existiert noch nicht; sie wird über
eine Migration in `belegung/migrations/` angelegt (nummerierte SQL-Dateien, siehe AGENTS.md).

## 4. Funktionale Anforderungen

- **FR-01:** Der Import liest eine ICS-Datei (RFC 5545) und extrahiert je `VEVENT` die Felder
  `UID`, `DTSTART`, `DTEND` (oder `DURATION`), `SUMMARY` und `RRULE`. Gefaltete Zeilen
  (Fortsetzung mit führendem Leerzeichen) werden entfaltet.
- **FR-02:** Zeitangaben mit `TZID` (nur IANA-Namen) und mit `Z`-Suffix werden nach UTC
  umgerechnet und als ISO 8601 gespeichert. Ganztägige Termine (`VALUE=DATE`) werden abgelehnt.
- **FR-03:** Termine mit `RRULE:FREQ=WEEKLY` (mit `COUNT` oder `UNTIL`, optional `INTERVAL`,
  `BYDAY`) werden in Einzeltermine expandiert; `EXDATE` entfernt einzelne Vorkommen.
- **FR-04:** Einzeltermine werden per `(uid, beginn_utc)` in die Tabelle `termin` geschrieben.
  Existiert der Schlüssel schon, werden Ende und Titel aktualisiert (Upsert); ein erneuter
  Import derselben Datei ändert nichts.
- **FR-05:** Nach dem Import gibt das Kommando einen Bericht aus: Anzahl neu, aktualisiert,
  unverändert und abgelehnt, und für jeden abgelehnten Termin UID und Grund. Exit-Code 1, wenn
  mindestens ein Termin abgelehnt wurde.
- **FR-06:** Mit `--dry-run` läuft der Import vollständig einschließlich Bericht, schreibt aber
  nichts in die Datenbank (Transaktion wird zurückgerollt).

## 5. Nicht-funktionale Anforderungen

- Nur Standardbibliothek (`sqlite3`, `zoneinfo`), Python ≥ 3.11.
- Der Import einer Datei läuft in genau einer Transaktion.
