---
id: SPEC-0003
title: logsum – Logdateien zusammenfassen
status: approved
---

# SPEC-0003: logsum – Logdateien zusammenfassen

## 1. Kontext

Betriebsteams wollen schnell sehen, wie viele Fehler und Warnungen in einer Menge von
Logdateien stehen. `logsum` ist ein Kommandozeilenwerkzeug in Python (nur Standardbibliothek,
`argparse`, `tomllib`). Eine Logzeile hat das Format
`2026-03-01T12:00:00Z LEVEL komponente: nachricht`, LEVEL ist eines von `DEBUG`, `INFO`,
`WARN`, `ERROR`.

## 2. Ziele

- Aufruf `logsum [OPTIONEN] DATEI...` gibt je Level die Anzahl der Zeilen aus.
- Wiederkehrende Einstellungen stehen in einer Konfigurationsdatei statt in jedem Aufruf.

## 3. Eingabeformat

- Dateien sind UTF-8; nicht dekodierbare Bytes werden ersetzt, nicht als Fehler behandelt.
- Leere Zeilen zählen nicht.

## 4. Funktionale Anforderungen

- **FR-01:** `logsum` liest alle angegebenen Dateien zeilenweise und zählt Zeilen je Level.
  Zeilen, die nicht dem Format entsprechen, werden als `UNPARSED` gezählt und nicht verworfen.
  Die Ausgabe ist eine Zeile je Level in fester Reihenfolge
  `ERROR`, `WARN`, `INFO`, `DEBUG`, `UNPARSED` im Format `LEVEL<TAB>ANZAHL`.
- **FR-02:** Mit `--format json` gibt `logsum` stattdessen ein JSON-Objekt
  `{"ERROR": n, "WARN": n, …}` mit denselben Schlüsseln aus. `--min-level WARN` blendet alle
  Level unterhalb der Schwelle aus (Reihenfolge `DEBUG` < `INFO` < `WARN` < `ERROR`;
  `UNPARSED` wird immer ausgegeben).
- **FR-03:** Einstellungen können in `~/.config/logsum/config.toml` stehen (Schlüssel
  `format`, `min_level`). Mit `--config PFAD` wird eine andere Datei gelesen. Fehlt die
  Standarddatei, gelten die Standardwerte (`format = "text"`, `min_level = "DEBUG"`);
  fehlt eine per `--config` genannte Datei, ist das ein Fehler.
- **FR-04:** Exit-Codes: 0 bei Erfolg, 1 wenn mindestens eine `ERROR`-Zeile gezählt wurde und
  `--fail-on-error` gesetzt ist, 2 bei Bedienfehlern (unbekannte Option, nicht lesbare Datei,
  ungültige Konfiguration). Fehlermeldungen gehen nach stderr, nie nach stdout.
- **FR-05:** Die Rangfolge der Einstellungen ist: Kommandozeile vor Umgebungsvariable
  `LOGSUM_MIN_LEVEL` (nur für `min_level`) vor Konfigurationsdatei vor Standardwert.

## 5. Nicht-Ziele

- Kein Folgen wachsender Dateien (`tail -f`).
- Keine komprimierten Eingaben (`.gz`).
- Keine Installation als Systempaket.
