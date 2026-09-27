---
id: SPEC-0003
title: "Tags, Fälligkeiten, Filter, Export und Undo"
type: feature
status: approved
owner: "Bench"
created: 2026-09-27
updated: 2026-09-27
version: 1.0.0
priority: medium
tags: [domain, service, persistence, cli, architecture]
depends_on: [SPEC-0001, SPEC-0002]
contracts: []
tests: []
---

# Tags, Fälligkeiten, Filter, Export und Undo

> **Status:** approved · **Owner:** Bench · **Version:** 1.0.0

## 1. Kontext & Motivation

Mit SPEC-0001 und SPEC-0002 lassen sich Aufgaben anlegen, bearbeiten, speichern und per CLI
bedienen. Diese Spec macht daraus ein brauchbares Werkzeug: Aufgaben bekommen Tags und
Fälligkeiten, lassen sich filtern und exportieren, und Änderungen lassen sich rückgängig machen.
Dabei gelten die Schichtregeln aus `AGENTS.md` und `.sdd/architecture.yaml` verbindlich.

## 2. Zielsetzung

**Primärziel:** Erweiterung von Modell, Service, Persistenz und CLI ohne Bruch der bestehenden
API und des bestehenden Dateiformats.

**Nicht-Ziele:** Undo über Neustarts hinweg, Undo in der CLI, Zeitzonen, Uhrzeiten.

## 3. Architektur & Design

- `Todo` erhält die Attribute `tags` (Tupel von `str`, aufsteigend sortiert, ohne Duplikate) und
  `due` (`datetime.date` oder `None`). Bestehende Aufrufe von `add(title)` bleiben gültig.
- Die Domänenlogik (Normalisierung von Tags, Validierung) liegt in `todo.domain`; der Export baut
  Zeichenketten und schreibt keine Dateien.
- Undo hält eine Historie von Zuständen im Service (Memento); die Historie wird nicht gespeichert.

## 4. Funktionale Anforderungen

- **FR-01:** **Tags beim Anlegen.** `add(title, tags=(), due=None)` nimmt optional ein Iterable von
  Tags an. Jeder Tag wird an den Enden von Leerzeichen befreit und in Kleinbuchstaben umgewandelt;
  danach muss er 1 bis 20 Zeichen aus `a`–`z`, `0`–`9` und `-` enthalten, sonst wirft `add`
  `ValidationError` und legt nichts an. `Todo.tags` enthält die normalisierten Tags ohne Duplikate,
  aufsteigend sortiert, als Tupel; ohne Tags ist es `()`.
- **FR-02:** **Tags ändern.** `tag(todo_id, *tags)` fügt Tags hinzu, `untag(todo_id, *tags)`
  entfernt sie; beide normalisieren wie FR-01 und geben die Aufgabe zurück. Einen bereits
  vorhandenen Tag erneut hinzuzufügen oder einen nicht vorhandenen zu entfernen ist kein Fehler.
  Ungültiger Tag: `ValidationError`, die Aufgabe bleibt unverändert. Unbekannte ID:
  `TodoNotFoundError`.
- **FR-03:** **Fälligkeit.** `add(..., due=datum)` und `set_due(todo_id, due)` setzen die
  Fälligkeit; `set_due(todo_id, None)` entfernt sie. `due` muss ein `datetime.date` sein, das kein
  `datetime.datetime` ist, oder `None`; andere Werte (auch Zeichenketten) ergeben
  `ValidationError` ohne Änderung. `set_due` gibt die Aufgabe zurück; unbekannte ID:
  `TodoNotFoundError`. Neue Aufgaben ohne Fälligkeit haben `due is None`.
- **FR-04:** **Überfällige Aufgaben.** `overdue(today)` gibt alle nicht erledigten Aufgaben mit
  `due < today` zurück, sortiert nach `due` aufsteigend, bei gleichem Datum nach `id`. Aufgaben
  ohne Fälligkeit, erledigte Aufgaben und Aufgaben mit `due == today` gehören nicht dazu.
- **FR-05:** **Filter.** `list_todos(done=None, tag=None, due_before=None, text=None)` (alle
  Parameter als Schlüsselwort) liefert die Aufgaben, die alle gesetzten Kriterien erfüllen,
  aufsteigend nach `id`: `done` (`True`/`False`) vergleicht den Status; `tag` verlangt den Tag
  (normalisiert wie FR-01, also ohne Rücksicht auf Groß-/Kleinschreibung); `due_before` verlangt
  eine Fälligkeit echt vor diesem Datum; `text` verlangt, dass der Titel den Text ohne Rücksicht auf
  Groß-/Kleinschreibung enthält. `None` bedeutet: kein Kriterium. Ohne Argumente gilt SPEC-0001
  FR-03 unverändert.
- **FR-06:** **Export.** `export_json()` gibt einen JSON-Text zurück: eine Liste mit je einem
  Objekt je Aufgabe, aufsteigend nach `id`, mit genau den Schlüsseln `id` (Zahl), `title`, `done`
  (Boolean), `tags` (Liste, sortiert) und `due` (`"JJJJ-MM-TT"` oder `null`). `export_csv()` gibt
  einen CSV-Text (Modul `csv`, Trennzeichen Komma, Quoting nach RFC 4180) zurück: Kopfzeile
  `id,title,done,tags,due`, danach je Aufgabe eine Zeile; `done` als `true`/`false`, `tags` mit `;`
  verbunden, `due` als `JJJJ-MM-TT` oder leer. Beide Exporte schreiben keine Dateien.
- **FR-07:** **Undo.** `undo()` macht die letzte erfolgreiche Änderung rückgängig und gibt `True`
  zurück; gibt es keine, gibt es `False` zurück und ändert nichts. Änderungen sind `add`,
  `complete`, `reopen`, `rename`, `delete`, `tag`, `untag` und `set_due`. Mehrfaches `undo()` geht
  schrittweise zurück bis zum Zustand beim Erzeugen des Service. Eine gelöschte Aufgabe kommt mit
  derselben ID, demselben Titel, Status, Tags und Fälligkeit zurück. Fehlgeschlagene Aufrufe
  erzeugen keinen Undo-Schritt. Der Zustand nach `undo()` wird wie jede Änderung gespeichert
  (SPEC-0002 FR-04). Eine rückgängig gemachte Aufgabe gibt ihre ID nicht wieder frei.
- **FR-08:** **Persistenz der neuen Felder.** Das Dateiformat aus SPEC-0002 FR-04 erhält je Aufgabe
  die Schlüssel `tags` (Liste von `str`) und `due` (`"JJJJ-MM-TT"` oder `null`). Tags und
  Fälligkeiten überdauern einen Neustart. Dateien im Format von SPEC-0002 (Einträge ohne `tags`
  und `due`) werden weiterhin geladen: fehlende Schlüssel bedeuten keine Tags bzw. keine
  Fälligkeit. Ein ungültiges Datum in `due` ist eine beschädigte Datei (`StorageError`).
- **FR-09:** **Kommandozeile.** Erweiterungen von `python -m todo` (SPEC-0002 FR-06):
  - `add TITEL [--tag TAG]… [--due JJJJ-MM-TT]`; die Ausgabe bleibt `#<id> <titel>`.
  - `list [--tag TAG] [--open | --done] [--search TEXT]` filtert wie FR-05 (`--open` = nicht
    erledigt). Zeilenformat: `[ ] #<id> <titel>`, bei Fälligkeit gefolgt von ` due:JJJJ-MM-TT`,
    bei Tags danach ` tags:<tag1>,<tag2>` (sortiert). Ohne Fälligkeit und Tags bleibt die Zeile
    wie in SPEC-0002.
  - `export --format json|csv` gibt den Text von `export_json()` bzw. `export_csv()` auf stdout aus.
  - Ungültiges Datum oder ungültiger Tag: Meldung auf stderr, Exit 1, Datei unverändert.
- **FR-10:** **Schichtregeln.** Die Abhängigkeiten zwischen den Paketen folgen `AGENTS.md` und
  `.sdd/architecture.yaml` (ARCH-01): `todo.domain` importiert kein anderes Paket von `todo`;
  `todo.service` importiert nur `todo.domain`; `todo.persistence` importiert nur `todo.domain`;
  `todo.cli` importiert nur `todo.service` und `todo.domain`. Nur der Einstieg (`todo/__init__.py`,
  `todo/__main__.py`) verbindet `todo.cli` mit `todo.persistence`. `todo.domain` importiert keine
  Module für Datei- oder Prozesszugriff (`os`, `io`, `pathlib`, `json`, `csv`, `shutil`,
  `subprocess`, `tempfile`). `JsonFileRepository` liegt in `todo.persistence` und `TodoService`
  in `todo.service`. `sdd arch check` meldet keine Verstöße.

## 5. Nicht-funktionale Anforderungen

| Kategorie | Anforderung |
|-----------|-------------|
| Abhängigkeiten | Nur Python-Standardbibliothek. |
| Kompatibilität | Alle Anforderungen von SPEC-0001 und SPEC-0002 bleiben erfüllt. |

## 6. Akzeptanzkriterien (Gherkin)

```gherkin
Feature: Tags, Fälligkeiten, Undo

  Scenario: Überfällige Aufgaben
    Given die Aufgaben "A" fällig am 2026-01-10 und "B" fällig am 2026-01-05
    When ich overdue(2026-01-20) aufrufe
    Then erhalte ich "B" vor "A"

  Scenario: Löschen rückgängig machen
    Given die Aufgabe #1 "A" mit Tag "home"
    When ich #1 lösche und undo() aufrufe
    Then ist #1 "A" mit Tag "home" wieder da
```

## 7. Edge Cases & Fehlerfälle

- `add("A", tags=["Home", "home "])` ergibt `tags == ("home",)`.
- `add("A", tags=["zu lang " * 5])` ergibt `ValidationError`.
- `undo()` direkt nach dem Erzeugen des Service gibt `False` zurück.
- Titel mit Komma oder Anführungszeichen werden im CSV korrekt gequotet.

## 8. Contracts

Keine; Service-API, Dateiformat, CLI und Schichtregeln sind in Abschnitt 4 festgelegt.

## 9. Tests

Unit-Tests unter `tests/unit/` (unittest), Marker `spec0003_frNN` im Testnamen.

## 10. Offene Fragen

Keine.

## 11. Änderungshistorie

| Datum      | Version | Autor | Änderung |
|------------|---------|-------|----------|
| 2026-09-27 | 1.0.0   | Bench | Fixture-Spec für die Benchmark-Suite e2e |
