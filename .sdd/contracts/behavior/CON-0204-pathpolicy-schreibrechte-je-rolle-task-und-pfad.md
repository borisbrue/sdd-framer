---
id: CON-0204
title: "PathPolicy: Schreibrechte je Rolle, Task und Pfad"
type: behavior
format: gherkin
spec: SPEC-0053
version: 0.2.0
status: approved
artifact: ".sdd/contracts/behavior/pathpolicy-schreibrechte-je-rolle-task-und-pfad.feature"
tests: ["TST-0233"]
---

# Contract: PathPolicy: Schreibrechte je Rolle, Task und Pfad

> **Spec:** SPEC-0053 · **Typ:** Verhalten (Gherkin) · **Status:** approved

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
| 2 | Rolle ist keine schreibende Rolle (`supervisor`, `reviewer`, `decomposer` oder unbekannt) | abgelehnt | `Rolle <rolle> schreibt nicht` |
| 3 | Pfad passt auf `.sdd/**`, `specs/**`, `contracts/**` oder `pipeline.protected_paths` | abgelehnt | `geschützter Pfad` |
| 4 | Pfad = `test_file` des Tasks und Rolle ≠ `test_author` | abgelehnt | `Testdatei des Tasks` |
| 5 | Pfad = `test_file` des Tasks und Rolle = `test_author` | erlaubt | – |
| 6 | Rolle = `test_author` und Pfad ≠ `test_file` | abgelehnt | `test_author schreibt nur die Testdatei` |
| 7 | Task hat `allowed_paths` und Pfad passt auf keines | abgelehnt | `außerhalb allowed_paths` |
| 8 | sonst (Rolle `implementer`) | erlaubt | – |

Schreibende Rollen sind abschließend `test_author` und `implementer` (sichere Basis: eine neue Rolle
darf nichts, bis sie ausdrücklich aufgenommen wird). `pipeline.protected_paths` ergänzt die
geschützten Pfade um projekteigene Globs (z. B. `docs/adr/**`), ohne diesen Contract zu ändern.

## Invarianten

- **INV-01:** Pfade werden vor der Prüfung normalisiert (`..`, `./`, doppelte `/`); Pfadflucht
  führt zu Regel 1.
- **INV-02:** Ein abgelehnter Schreibvorgang wird nicht ausgeführt, als Ereignis `write_rejected`
  mit Rolle, Pfad und Grund protokolliert (CON-0202) und macht den Rollenaufruf zu
  `outcome: gate_failed`.
- **INV-03:** Das Ergebnis hängt nur von Rolle, Task, Pfad und `pipeline.protected_paths` ab, nie
  vom Provider oder Modus.
- **INV-05:** Unbekannte Rollen und Rollen ohne Schreibrecht werden immer abgelehnt (Default deny).
- **INV-04:** Die Globs folgen derselben Semantik wie in SPEC-0054 (`**` über Verzeichnisgrenzen).

## Begriffe

| Begriff | Definition |
|---------|------------|
| Schreibvorgang | Anlegen, Ändern oder Löschen einer Datei durch das Ergebnis eines Rollenaufrufs |
| allowed_paths | Globs des Tasks aus der Zerlegung (CON-0200, CON-0203) |
