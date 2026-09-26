---
id: SPEC-0101
title: "ID-Vergabe für SDD-Artefakte"
status: approved
---
# SPEC-0101: ID-Vergabe für SDD-Artefakte

## 1. Kontext

`sdd new` legt Specs, Contracts und Testdokumente an. Jede Datei bekommt eine ID der Form
`<PRÄFIX>-<NUMMER>`, z. B. `SPEC-0007` oder `CON-0112`. Die Funktion, die die nächste
freie ID bestimmt, bekommt die bereits vergebenen IDs aller Arten als Liste von Strings.

## 4. Funktionale Anforderungen

- **FR-01:** `next_id(existing, prefix, padding=4)` liefert `<prefix>-<n>`, wobei `n` die
  größte bereits vergebene Nummer dieses Präfixes plus 1 ist. Lücken in der Nummerierung
  (z. B. gelöschte Specs) werden nicht wiederverwendet. Gibt es noch keine ID des Präfixes,
  ist `n` = 1.
- **FR-02:** Es zählen nur IDs, die exakt dem Muster `<prefix>-<Ziffern>` entsprechen. IDs
  anderer Präfixe (`CON-0200` beim Präfix `SPEC`) und abweichende Einträge
  (`SPEC-0003-entwurf`, `SPEC-XY`) werden ignoriert. Nummern werden numerisch verglichen;
  ältere IDs ohne führende Nullen (`SPEC-9`, `SPEC-12`) zählen mit.
- **FR-03:** Die Nummer wird mit führenden Nullen auf `padding` Stellen aufgefüllt; ist sie
  länger, wird sie nicht gekürzt (`SPEC-10000`). `padding` kleiner als 1 ist ein Fehler
  (`ValueError`).

## 5. Nicht-Ziele

- Dateisystem-Zugriff: die Funktion bekommt die IDs als Liste.
