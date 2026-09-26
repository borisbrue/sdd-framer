# SPEC-0101: FR-IDs aus Spec-Dokumenten extrahieren

## 1. Zusammenfassung

Die Compliance-Kette muss wissen, welche funktionalen Anforderungen (FRs) eine Spec deklariert.
`sddlib.fr_ids.extract_fr_ids(body)` liefert die FR-IDs aus dem Markdown-Body einer Spec.

## 2. Kontext

Bisher zählte jede Nennung von `FR-\d+` im Dokument als Anforderung. Dadurch wurden Querverweise
auf fremde Specs („siehe SPEC-0016 FR-18“) als eigene FRs gezählt, und `sdd spec approve` brach
mit einer FR ab, die es gar nicht gab.

## 3. Nicht-Ziele

- Keine Prüfung, ob die Nummern lückenlos sind.
- Kein Parsen von Frontmatter (der Body kommt ohne Frontmatter an).

## 4. Funktionale Anforderungen

- **FR-01:** Der Anforderungsabschnitt beginnt bei einer Überschrift der Ebene 2 oder 3 (`##` oder
  `###`), deren Text „Funktionale Anforderungen“ lautet, optional mit vorangestellter Nummer wie
  `4. ` und unabhängig von Groß-/Kleinschreibung. Fehlt der Abschnitt, ist das Ergebnis eine leere
  Liste.
- **FR-02:** Der Abschnitt endet an der nächsten Überschrift derselben oder einer höheren Ebene
  (bei `##` also an der nächsten `#` oder `##`, nicht an einer `###`-Unterüberschrift), sonst am
  Dokumentende. FR-IDs außerhalb des Abschnitts zählen nicht.
- **FR-03:** Eine FR gilt als deklariert, wenn ihre ID (`FR-` gefolgt von Ziffern) am Zeilenanfang
  steht – nach optionaler Einrückung, optionalem Listenmarker (`-`, `*`, `+`), optionaler
  Checkbox (`[ ]`, `[x]`) und optionaler Fettung (`**`). Nennungen mitten im Fließtext sind
  Querverweise und zählen nicht.
- **FR-04:** Das Ergebnis enthält jede ID genau einmal, in der Reihenfolge des ersten Auftretens.

## 5. Akzeptanzkriterien

- `- **FR-01:** …` und `- FR-02: …` und `**FR-03**` werden erkannt.
- „aus SPEC-0016 (FR-18–FR-20)“ im Fließtext erzeugt keine FR-18.
