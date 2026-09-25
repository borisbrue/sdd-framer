---
id: CON-0204
title: "PathPolicy: Schreibrechte je Rolle, Task und Pfad"
type: behavior
format: gherkin
spec: SPEC-0053
version: 0.1.0
status: draft
artifact: ".sdd/contracts/behavior/pathpolicy-schreibrechte-je-rolle-task-und-pfad.feature"
tests: ["TST-0233"]
---

# Contract: PathPolicy: Schreibrechte je Rolle, Task und Pfad

> **Spec:** SPEC-0053 · **Typ:** Verhalten (Gherkin) · **Status:** draft

## Zweck

Legt fest, welche Rolle in einem Run welche Dateien schreiben darf (SPEC-0053 FR-07, FR-09). Die
Policy ist unabhängig vom Provider: Der Mediator wendet sie auf jeden Schreibvorgang an, und
Provider enthalten keine eigenen Pfadregeln.

## Garantien

Die Szenarien im Artifact (`.sdd/contracts/behavior/pathpolicy-schreibrechte-je-rolle-task-und-pfad.feature`)
sind **ausführbare Spezifikation**. Jedes Szenario MUSS durch einen automatisierten Test (pytest)
abgedeckt sein.

## Regeln (in dieser Reihenfolge, die erste zutreffende entscheidet)

| # | Bedingung | Ergebnis | Grund |
|---|-----------|----------|-------|
| 1 | Pfad nach Normalisierung außerhalb der Projektwurzel | abgelehnt | `geschützter Pfad` |
| 2 | Rolle `supervisor` | abgelehnt | `Rolle supervisor schreibt nicht` |
| 3 | Pfad passt auf `.sdd/**`, `specs/**`, `contracts/**` | abgelehnt | `geschützter Pfad` |
| 4 | Rolle `implementer` und Pfad = `test_file` des Tasks | abgelehnt | `Testdatei des Tasks` |
| 5 | Rolle `test_author` und Pfad = `test_file` des Tasks | erlaubt | – |
| 6 | Task hat `allowed_paths` und Pfad passt auf keines | abgelehnt | `außerhalb allowed_paths` |
| 7 | sonst | erlaubt | – |

## Invarianten

- **INV-01:** Pfade werden vor der Prüfung normalisiert (`..`, `./`, doppelte `/`); Pfadflucht
  führt zu Regel 1.
- **INV-02:** Ein abgelehnter Schreibvorgang wird nicht ausgeführt, als Ereignis `write_rejected`
  mit Rolle, Pfad und Grund protokolliert (CON-0202) und macht den Rollenaufruf zu
  `outcome: gate_failed`.
- **INV-03:** Das Ergebnis hängt nur von Rolle, Task und Pfad ab, nie vom Provider oder Modus.
- **INV-04:** Die Globs folgen derselben Semantik wie in SPEC-0054 (`**` über Verzeichnisgrenzen).

## Begriffe

| Begriff | Definition |
|---------|------------|
| Schreibvorgang | Anlegen, Ändern oder Löschen einer Datei durch das Ergebnis eines Rollenaufrufs |
| allowed_paths | Globs des Tasks aus der Zerlegung (CON-0200, CON-0203) |
