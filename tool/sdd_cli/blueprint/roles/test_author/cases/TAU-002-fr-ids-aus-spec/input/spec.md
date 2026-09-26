---
id: SPEC-0102
title: "FR-Parser für Spec-Dokumente"
status: approved
---
# SPEC-0102: FR-Parser für Spec-Dokumente

## 1. Kontext

Die Compliance-Kette prüft, ob jede funktionale Anforderung einer Spec einen Test hat. Dazu
muss sie die deklarierten FR-IDs aus dem Markdown-Body einer Spec lesen. Früher zählte jede
Nennung von `FR-<n>` im Abschnitt; Querverweise auf fremde Specs erzeugten so Phantom-FRs.

## 4. Funktionale Anforderungen

- **FR-01:** `extract_fr_ids(body)` findet den Abschnitt, dessen Überschrift (Ebene 2 oder
  3, also `##` oder `###`) „Funktionale Anforderungen“ lautet, optional mit vorangestellter
  Nummer (`## 4. Funktionale Anforderungen`), ohne Beachtung der Groß-/Kleinschreibung.
  Gibt es keinen solchen Abschnitt, ist das Ergebnis eine leere Liste.
- **FR-02:** Der Abschnitt endet erst an der nächsten Überschrift gleicher oder höherer
  Ebene. Unterüberschriften tieferer Ebene (z. B. `### Export` unter einer `##`-Sektion)
  gehören noch dazu.
- **FR-03:** Eine FR gilt nur als deklariert, wenn ihre ID am Zeilenanfang steht – nach
  optionaler Einrückung, optionalem Listenmarker (`-`, `*`, `+`), optionaler Checkbox
  (`[ ]`, `[x]`) und optionaler Fettung (`**`). Nennungen im Fließtext (Querverweise wie
  „siehe SPEC-0016 FR-18“) zählen nicht. Das Ergebnis enthält jede ID einmal, in der
  Reihenfolge des ersten Auftretens.

## 5. Nicht-Ziele

- Validierung der Nummerierung (Lücken, Reihenfolge) – das macht ein anderer Check.
