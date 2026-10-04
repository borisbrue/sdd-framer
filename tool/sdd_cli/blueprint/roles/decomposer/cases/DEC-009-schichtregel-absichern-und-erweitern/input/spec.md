---
id: SPEC-0110
title: Fälligkeiten und Schichtregel
status: approved
---

# SPEC-0110: Fälligkeiten und Schichtregel

## 1. Kontext

Die Todo-Verwaltung (Paket `todo/`) kann Todos anlegen, erledigen und umbenennen. Die Schichten
stehen in AGENTS.md: `todo/domain.py` (Fachobjekte), `todo/repository.py` (Ablage),
`todo/service.py` (Anwendungsfälle). Der bestehende Code hält die Schichtregel bereits ein,
sie ist aber durch keinen Test gesichert.

## 2. Funktionale Anforderungen

- **FR-01:** `TodoService.set_due(todo_id, due)` setzt ein Fälligkeitsdatum (`datetime.date`)
  oder entfernt es mit `None`. `Todo` bekommt dafür das Feld `due` (Default `None`); bestehende
  Aufrufe von `Todo(...)` bleiben gültig.
- **FR-02:** `TodoService.overdue(today)` liefert alle offenen Todos, deren Fälligkeit vor
  `today` liegt, sortiert nach Fälligkeit und dann nach ID. Erledigte Todos und Todos ohne
  Fälligkeit erscheinen nie.
- **FR-03:** Die Schichtregel aus AGENTS.md wird durch einen Test abgesichert: `todo/domain.py`
  importiert weder `todo.repository` noch `todo.service`, `todo/repository.py` importiert
  `todo.service` nicht. Der bestehende Code erfüllt die Regel bereits; es ist nichts zu ändern,
  nur der Test fehlt.

## 3. Nicht-Ziele

- Keine Erinnerungen oder Benachrichtigungen bei Fälligkeit.
- Keine Zeitzonen; Fälligkeit ist ein Datum ohne Uhrzeit.
