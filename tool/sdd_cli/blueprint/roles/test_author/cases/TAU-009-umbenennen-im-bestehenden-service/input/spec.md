---
id: SPEC-0109
title: Todos umbenennen
status: approved
---

# SPEC-0109: Todos umbenennen

## 1. Kontext

Die Todo-Verwaltung (Paket `todo/`) kann Todos anlegen und erledigen. Fachobjekte und Regeln
stehen in `todo/domain.py`, die Ablage in `todo/repository.py` (`InMemoryRepository`), die
Anwendungsfälle in `todo/service.py` (`TodoService`). Diese Spec ergänzt das Umbenennen.

## 2. Funktionale Anforderungen

- **FR-01:** `TodoService.rename(todo_id, title)` setzt den Titel eines bestehenden Todos und
  gibt das geänderte Todo zurück. Der neue Titel wird gespeichert: Ein späteres Lesen aus der
  Ablage liefert ihn. ID und Erledigt-Status bleiben unverändert.
- **FR-02:** Für den neuen Titel gelten dieselben Regeln wie beim Anlegen: Leerraum an den
  Rändern wird entfernt; ein leerer Titel oder einer mit mehr als 200 Zeichen ist ein
  `ValidationError`, und das Todo bleibt unverändert.
- **FR-03:** Gibt es kein Todo mit `todo_id`, wirft `rename` einen `TodoNotFoundError`; es wird
  nichts angelegt.

## 3. Nicht-Ziele

- Keine Änderung an `todo/domain.py` oder `todo/repository.py`.
- Keine Persistenz außerhalb des Speichers.
