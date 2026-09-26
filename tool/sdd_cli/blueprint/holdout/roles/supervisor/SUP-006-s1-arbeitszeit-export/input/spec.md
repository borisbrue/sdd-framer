---
id: SPEC-0022
title: "Monatsexport der Arbeitszeiten für die Lohnbuchhaltung"
status: approved
---

# SPEC-0022: Monatsexport der Arbeitszeiten für die Lohnbuchhaltung

## 1. Kontext

Die Zeiterfassung (`stempel`) speichert Kommen/Gehen-Buchungen je Mitarbeiter. Die externe
Lohnbuchhaltung erwartet monatlich eine CSV-Datei.

## 2. Funktionale Anforderungen

- **FR-01:** `stempel export --monat 2026-08` erzeugt `export/2026-08.csv` mit einer Zeile je
  Mitarbeiter und Arbeitstag (Personalnummer, Datum, Arbeitsminuten, Pausenminuten).
- **FR-02:** Paare aus Kommen/Gehen werden zu Arbeitszeit verrechnet; ein Kommen ohne Gehen
  wird nicht exportiert, sondern in `export/2026-08.fehler.txt` gemeldet.
- **FR-03:** Gesetzliche Pausen werden abgezogen, wenn weniger gebucht wurde: ab 6 h Arbeit
  30 min, ab 9 h 45 min.
- **FR-04:** Die Arbeitsminuten eines Tages werden nach dem Pausenabzug kaufmännisch auf volle
  Viertelstunden gerundet (7 min → 0, 8 min → 15).
- **FR-05:** Die CSV nutzt `;` als Trenner, UTF-8 mit BOM und CRLF-Zeilenenden (Vorgabe der
  Lohnsoftware).

## 3. Nicht-Ziele

- Keine Überstundenkonten, kein Urlaub.
