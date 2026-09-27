---
id: SPEC-0001
title: "Aufgaben anlegen und auflisten"
type: feature
status: approved
owner: "Bench"
created: 2026-09-27
updated: 2026-09-27
version: 1.0.0
priority: high
tags: [domain, service]
depends_on: []
contracts: []
tests: []
---

# Aufgaben anlegen und auflisten

> **Status:** approved · **Owner:** Bench · **Version:** 1.0.0

## 1. Kontext & Motivation

`todo-service` verwaltet Aufgaben (Todos). Das Paket `todo/` enthält bisher nur das Gerüst der
Schichten `domain`, `service`, `persistence` und `cli` (siehe `AGENTS.md`). Diese Spec liefert den
Kern: das Domänenmodell und einen Service, der Aufgaben im Speicher anlegt und auflistet.

## 2. Zielsetzung

**Primärziel:** Eine Service-API, mit der sich Aufgaben anlegen und in fester Reihenfolge
auflisten lassen.

**Nicht-Ziele:** Persistenz, Kommandozeile, Ändern oder Löschen von Aufgaben (SPEC-0002).

## 3. Architektur & Design

- `todo.domain` enthält das Modell `Todo` und die Ausnahme `ValidationError`, ohne Ein-/Ausgabe.
- `todo.service` enthält `TodoService`; ohne Argument hält er die Aufgaben im Speicher.
- Öffentliche Namen werden aus dem jeweiligen Paket re-exportiert (`from todo.domain import Todo`,
  `from todo.service import TodoService`).

## 4. Funktionale Anforderungen

- **FR-01:** **Anlegen.** `TodoService()` (ohne Argumente) startet mit einer leeren Aufgabenliste.
  `add(title)` legt eine Aufgabe an und gibt sie als `todo.domain.Todo` zurück. Ein `Todo` hat die
  Attribute `id` (`int`), `title` (`str`) und `done` (`bool`). Die erste Aufgabe erhält die ID 1,
  jede weitere die nächsthöhere ganze Zahl. Der Titel wird an beiden Enden von Leerzeichen befreit
  gespeichert; `done` ist bei neuen Aufgaben `False`.
- **FR-02:** **Titel-Validierung.** Ist der Titel nach dem Befreien von Leerzeichen leer oder
  länger als 200 Zeichen, oder ist er kein `str`, wirft `add` die Ausnahme
  `todo.domain.ValidationError` (Unterklasse von `ValueError`) mit einer deutschsprachigen Meldung.
  Genau 200 Zeichen sind erlaubt. Eine abgelehnte Aufgabe wird nicht angelegt und verbraucht keine
  ID.
- **FR-03:** **Auflisten.** `list_todos()` gibt eine neue Liste aller Aufgaben zurück, aufsteigend
  nach `id` (also in Anlagereihenfolge). Ohne Aufgaben ist die Liste leer. Änderungen an der
  zurückgegebenen Liste (z. B. `clear()`, `append`) wirken sich nicht auf den Service aus.

## 5. Nicht-funktionale Anforderungen

| Kategorie | Anforderung |
|-----------|-------------|
| Abhängigkeiten | Nur Python-Standardbibliothek (≥ 3.10). |
| Schichten | `todo.domain` importiert nichts aus anderen Schichten; `todo.service` nur `todo.domain`. |

## 6. Akzeptanzkriterien (Gherkin)

```gherkin
Feature: Aufgaben anlegen

  Scenario: Zwei Aufgaben anlegen
    Given ein neuer TodoService
    When ich "  Milch kaufen " und "Steuer" anlege
    Then listet list_todos() die Aufgaben #1 "Milch kaufen" und #2 "Steuer", beide nicht erledigt

  Scenario: Leerer Titel
    When ich "   " anlege
    Then wird ValidationError geworfen und die Liste bleibt leer
```

## 7. Edge Cases & Fehlerfälle

- Titel aus genau 200 Zeichen ist gültig, 201 Zeichen nicht.
- Nach einem abgelehnten `add` erhält die nächste gültige Aufgabe die ID, die sie ohne den Fehler
  bekommen hätte.

## 8. Contracts

Keine; die Service-API ist in Abschnitt 4 festgelegt.

## 9. Tests

Unit-Tests unter `tests/unit/` (unittest), Marker `spec0001_frNN` im Testnamen.

## 10. Offene Fragen

Keine.

## 11. Änderungshistorie

| Datum      | Version | Autor | Änderung |
|------------|---------|-------|----------|
| 2026-09-27 | 1.0.0   | Bench | Fixture-Spec für die Benchmark-Suite e2e |
