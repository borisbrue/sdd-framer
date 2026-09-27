---
id: SPEC-0002
title: "Aufgaben bearbeiten, in JSON speichern und per CLI bedienen"
type: feature
status: approved
owner: "Bench"
created: 2026-09-27
updated: 2026-09-27
version: 1.0.0
priority: high
tags: [service, persistence, cli]
depends_on: [SPEC-0001]
contracts: []
tests: []
---

# Aufgaben bearbeiten, in JSON speichern und per CLI bedienen

> **Status:** approved · **Owner:** Bench · **Version:** 1.0.0

## 1. Kontext & Motivation

SPEC-0001 liefert Anlegen und Auflisten im Speicher. Diese Spec ergänzt das Bearbeiten von
Aufgaben, eine Persistenz als JSON-Datei und eine Kommandozeile.

## 2. Zielsetzung

**Primärziel:** Aufgaben lassen sich abrufen, erledigen, wieder öffnen, umbenennen und löschen;
der Zustand überdauert einen Neustart; `python -m todo` bedient den Service.

**Nicht-Ziele:** Tags, Fälligkeiten, Filter, Export, Undo (SPEC-0003).

## 3. Architektur & Design

- Fehlertypen der Domäne liegen in `todo.domain`, der Speicherfehler in `todo.persistence`.
- `todo.persistence.JsonFileRepository` wird dem Service injiziert (`TodoService(repository)`);
  `todo.service` importiert `todo.persistence` nicht. Die Verdrahtung für die Kommandozeile
  übernimmt der Einstieg `todo/__main__.py`.
- Ohne Argument behält `TodoService()` das Verhalten aus SPEC-0001 (Speicher, keine Datei).

## 4. Funktionale Anforderungen

- **FR-01:** **Abrufen und Erledigen.** `get(todo_id)` gibt die Aufgabe mit dieser ID zurück.
  `complete(todo_id)` setzt `done` auf `True` und gibt die geänderte Aufgabe zurück; ein zweiter
  Aufruf ist erlaubt und lässt `done` auf `True`. Für eine unbekannte ID werfen `get` und
  `complete` die Ausnahme `todo.domain.TodoNotFoundError` (Unterklasse von `LookupError`).
- **FR-02:** **Wieder öffnen und Löschen.** `reopen(todo_id)` setzt `done` auf `False` und gibt die
  Aufgabe zurück. `delete(todo_id)` entfernt die Aufgabe; danach fehlt sie in `list_todos()` und
  `get` wirft `TodoNotFoundError`. Beide werfen für eine unbekannte ID `TodoNotFoundError`. IDs
  werden nie wiederverwendet: Auch nach dem Löschen der Aufgabe mit der höchsten ID erhält die
  nächste neue Aufgabe eine höhere ID als jede bisher vergebene.
- **FR-03:** **Umbenennen.** `rename(todo_id, title)` ändert den Titel mit denselben Regeln wie
  `add` (Leerzeichen an den Enden entfernen, `ValidationError` bei leerem, zu langem oder
  nicht-`str`-Titel) und gibt die Aufgabe zurück. Bei einem Fehler bleibt der alte Titel erhalten.
  Unbekannte ID: `TodoNotFoundError`.
- **FR-04:** **JSON-Persistenz.** `todo.persistence.JsonFileRepository(path)` speichert in der
  Datei `path` (`str` oder `pathlib.Path`). `TodoService(repository)` lädt beim Erzeugen den
  Zustand und schreibt ihn nach jeder erfolgreichen Änderung (`add`, `complete`, `reopen`,
  `rename`, `delete`) vollständig in die Datei. Eine fehlende Datei bedeutet: keine Aufgaben; sie
  wird bei der ersten Änderung angelegt. Dateiformat (UTF-8):
  `{"next_id": <int>, "todos": [{"id": <int>, "title": <str>, "done": <bool>}, …]}` mit den
  Aufgaben aufsteigend nach `id`; `next_id` ist die ID der nächsten neuen Aufgabe. Ein neuer Service
  mit derselben Datei sieht dieselben Aufgaben mit Titel und Status und setzt die IDs fort
  (FR-02 gilt über Neustarts hinweg).
- **FR-05:** **Beschädigte Datei.** Enthält die Datei kein gültiges JSON oder nicht die Struktur aus
  FR-04 (z. B. eine Liste statt eines Objekts, fehlendes `todos`, ein Eintrag ohne `id`), wirft das
  Laden `todo.persistence.StorageError` (Unterklasse von `Exception`), spätestens beim Erzeugen des
  `TodoService` oder beim ersten Aufruf von `list_todos()`. Die Datei bleibt dabei unverändert.
- **FR-06:** **Kommandozeile.** `python -m todo [--file PFAD] BEFEHL …` arbeitet auf der Datei
  `PFAD` (Default: `todo.json` im aktuellen Verzeichnis) über `JsonFileRepository`:
  - `add TITEL` legt eine Aufgabe an und gibt `#<id> <titel>` aus (Titel wie gespeichert).
  - `list` gibt je Aufgabe eine Zeile `[ ] #<id> <titel>` bzw. `[x] #<id> <titel>` (erledigt) aus,
    aufsteigend nach ID; ohne Aufgaben keine Ausgabe.
  - `done ID`, `reopen ID` und `delete ID` wirken wie die gleichnamigen Service-Methoden
    (`done` = `complete`).
  - Erfolg: Exit 0. Validierungsfehler, unbekannte ID und beschädigte Datei: eine Meldung auf
    stderr, nichts auf stdout, Exit 1, die Datei bleibt unverändert.

## 5. Nicht-funktionale Anforderungen

| Kategorie | Anforderung |
|-----------|-------------|
| Abhängigkeiten | Nur Python-Standardbibliothek. |
| Schichten | `todo.persistence` importiert nur `todo.domain`; `todo.cli` nur `todo.service` und `todo.domain`. |
| Robustheit | Die Datei wird atomar ersetzt (temporäre Datei + `os.replace`). |

## 6. Akzeptanzkriterien (Gherkin)

```gherkin
Feature: Bearbeiten und Speichern

  Scenario: Zustand überdauert einen Neustart
    Given ein TodoService mit JsonFileRepository auf "todo.json"
    When ich "A" und "B" anlege und #1 erledige
    Then sieht ein neuer TodoService auf derselben Datei #1 erledigt und #2 offen

  Scenario: CLI
    When ich "python -m todo --file t.json add Brot" ausführe
    Then ist die Ausgabe "#1 Brot" und der Exit-Code 0
```

## 7. Edge Cases & Fehlerfälle

- `delete` der einzigen Aufgabe, dann `add`: neue ID ist 2.
- `done 99` bei unbekannter ID: Exit 1, Meldung auf stderr.
- Leere Datei (0 Bytes) gilt als beschädigt (FR-05).

## 8. Contracts

Keine; Service-API, Dateiformat und CLI sind in Abschnitt 4 festgelegt.

## 9. Tests

Unit-Tests unter `tests/unit/` (unittest), Marker `spec0002_frNN` im Testnamen.

## 10. Offene Fragen

Keine.

## 11. Änderungshistorie

| Datum      | Version | Autor | Änderung |
|------------|---------|-------|----------|
| 2026-09-27 | 1.0.0   | Bench | Fixture-Spec für die Benchmark-Suite e2e |
