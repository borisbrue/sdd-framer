---
id: SPEC-0044
title: "Dauerangaben in der Konfiguration"
status: approved
---
# SPEC-0044: Dauerangaben in der Konfiguration

## 1. Kontext
Timeouts und Wartezeiten stehen in der Konfiguration als lesbare Dauer (`"90s"`, `"1h30m"`).
Das Werkzeug rechnet intern in ganzen Sekunden.

## 4. Funktionale Anforderungen

- **FR-01:** `parse_duration(text)` wandelt eine Dauer aus einer oder mehreren Komponenten
  `<ganze Zahl><Einheit>` in Sekunden um. Einheiten: `d` (86400 s), `h` (3600 s), `m` (60 s),
  `s` (1 s). Komponenten stehen direkt hintereinander ohne Leerzeichen (`"1d2h3m4s"`); führender
  und abschließender Leerraum sowie Großschreibung (`" 2H "`) sind erlaubt. Eine reine Zahl ohne
  Einheit gilt als Sekunden (`"45"` → 45). `"0s"` ist gültig und ergibt 0.
- **FR-02:** Ungültige Angaben lösen `DurationError` (Unterklasse von `ValueError`) aus: leerer
  oder nur aus Leerraum bestehender Text, unbekannte Einheit (`"5w"`), fehlende Zahl (`"h"`),
  Zahl ohne Einheit hinter einer Komponente (`"1h30"`), negative oder gebrochene Zahlen
  (`"-5s"`, `"1.5h"`), Leerzeichen zwischen Komponenten sowie Einheiten, die doppelt oder
  nicht in absteigender Reihenfolge `d, h, m, s` vorkommen (`"1m1h"`, `"1h1h"`).
