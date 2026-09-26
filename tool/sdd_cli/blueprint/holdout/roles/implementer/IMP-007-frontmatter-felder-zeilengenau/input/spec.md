---
id: SPEC-0131
title: "Artefakte ablösen"
status: approved
---
# SPEC-0131: Artefakte ablösen

## 1. Kontext
Beim Ablösen einer Spec schreibt das Werkzeug `deprecated_reason` und `replaced_by` ins
Frontmatter. Artefakte stehen unter Versionskontrolle; Diffs sollen nur die betroffenen Zeilen
zeigen. Deshalb wird das Frontmatter nicht per YAML neu serialisiert, sondern zeilengenau geändert.

## 2. Nicht-Ziele
- Keine verschachtelten Felder, Listen oder mehrzeiligen Werte.
- Kein Umsortieren oder Umformatieren bestehender Felder.

## 4. Funktionale Anforderungen

- **FR-01:** `set_frontmatter_fields(path, fields)` setzt für jedes Paar aus `fields` (in dessen
  Reihenfolge) die Zeile `<key>: <wert>`, wobei der Wert als JSON-String geschrieben wird
  (`json.dumps`, Nicht-ASCII-Zeichen bleiben unverändert, z. B. `reason: "Überholt"`).
- **FR-02:** Existiert im Frontmatter bereits eine Zeile, die am Zeilenanfang mit `<key>:` beginnt,
  wird genau die erste solche Zeile ersetzt. Schlüssel sind wörtlich zu nehmen (Sonderzeichen wie
  `.` sind keine Muster); ein Feld `status_note` ist nicht das Feld `status`, und Zeilen im Rumpf
  nach dem Frontmatter werden nie verändert.
- **FR-03:** Fehlt das Feld, wird die Zeile am Ende des Frontmatter-Blocks angehängt (nach dem
  letzten Feld, ohne Leerzeilen dazwischen; abschließender Leerraum des Blocks entfällt dabei).
- **FR-04:** Alles außerhalb der geänderten bzw. angehängten Zeilen bleibt byte-gleich, auch die
  Trennzeilen `---` und der Rumpf. Hat die Datei kein Frontmatter (Erkennung über
  `sddlib.frontmatter.FRONTMATTER_RE`), wird `FrontmatterError` (eigene Exception-Klasse im Modul)
  mit dem Dateinamen in der Meldung ausgelöst und die Datei nicht verändert.
