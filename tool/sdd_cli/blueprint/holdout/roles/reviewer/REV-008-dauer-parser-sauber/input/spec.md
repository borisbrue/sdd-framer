---
id: SPEC-0003
title: "Dauer als Kommandozeilenargument"
status: approved
---

# SPEC-0003: Dauer als Kommandozeilenargument

## 1. Kontext

Der Pomodoro-Timer `tempo` nimmt bisher nur Minuten als Ganzzahl. Nutzer wollen Dauern wie
`1h30m` oder `90s` angeben.

## 2. Funktionale Anforderungen

- **FR-01:** `parse_dauer(text)` in `tempo/zeit.py` wandelt eine Dauer aus Stunden (`h`),
  Minuten (`m`) und Sekunden (`s`) in Sekunden (int) um. Jede Einheit darf höchstens einmal
  und nur in der Reihenfolge h → m → s vorkommen, jeweils mit einer nicht-negativen Ganzzahl
  davor; Werte über 59 sind erlaubt (`90m` = 5400). Einheiten sind kleingeschrieben, zwischen
  den Teilen steht kein Leerzeichen; Leerraum am Anfang und Ende wird ignoriert.
- **FR-02:** Ungültige Eingaben (leer, unbekannte Einheit, Zahl ohne Einheit, falsche
  Reihenfolge, doppelte Einheit, Dezimal- oder negative Zahlen), eine Gesamtdauer von 0 und
  Dauern über 24 Stunden lösen `ValueError` mit verständlicher Meldung aus. Genau 24 h ist
  erlaubt.
- **FR-03:** `tempo start <dauer>` nutzt `parse_dauer` (eigener Task T02).
