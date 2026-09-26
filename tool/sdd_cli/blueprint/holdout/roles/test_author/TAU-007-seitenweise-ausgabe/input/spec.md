---
id: SPEC-0061
title: "Seitenweise Listenausgabe"
status: approved
---
# SPEC-0061: Seitenweise Listenausgabe

## 1. Kontext
`sdd list` gibt in großen Projekten Hunderte Artefakte aus. Die Ausgabe wird in Seiten geteilt;
die Oberfläche zeigt „Seite 2 von 7“ und einen Hinweis, ob es weitergeht.

## 4. Funktionale Anforderungen

- **FR-01:** `paginate(items, page=1, per_page=20)` liefert ein `Page` mit den Einträgen der
  angefragten Seite (Seiten zählen ab 1; Seite `p` enthält die Einträge mit Index
  `(p-1)*per_page` bis ausschließlich `p*per_page`), außerdem `page`, `per_page`,
  `total_items` (Anzahl aller Einträge) und `total_pages` (aufgerundet, mindestens 1 – auch
  eine leere Liste hat eine Seite).
- **FR-02:** `has_next` ist genau dann wahr, wenn es nach der angefragten Seite noch eine Seite
  gibt. Eine Seite hinter der letzten ist kein Fehler: sie liefert eine leere Eintragsliste und
  `has_next = False`.
- **FR-03:** `per_page` muss zwischen 1 und 100 liegen (beide inklusive), `page` mindestens 1;
  sonst `ValueError`. Die übergebene Liste wird nicht verändert.
