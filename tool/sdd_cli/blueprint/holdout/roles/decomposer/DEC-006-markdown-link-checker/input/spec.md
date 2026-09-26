---
id: SPEC-0012
title: "linkwart – Prüfung interner Links in Markdown-Dokumentation"
status: approved
---

# SPEC-0012: linkwart – Prüfung interner Links in Markdown-Dokumentation

## 1. Kontext

Unsere Projektdokumentation (`docs/`, ca. 400 Markdown-Dateien) verweist über relative Links
und Anker aufeinander. Nach Umbenennungen bleiben regelmäßig tote Links zurück, die erst Leser
bemerken. `linkwart` ist ein kleines Python-CLI, das in der CI läuft und tote interne Links
meldet.

## 2. Ziele

- Tote relative Links und Anker vor dem Merge finden.
- Maschinenlesbare Ausgabe für die CI-Annotation.

## 3. Nicht-Ziele

- **Keine Prüfung externer Links** (`http://`, `https://`, `mailto:`). Sie werden erkannt und
  übersprungen, aber nie aufgerufen – die CI hat keinen Netzzugang.
- Keine automatische Reparatur von Links.
- Kein HTML-Rendering; Links in eingebettetem HTML (`<a href>`) werden ignoriert.

## 4. Funktionale Anforderungen

- **FR-01:** `linkwart check <verzeichnis>` findet rekursiv alle `*.md`-Dateien und extrahiert
  daraus Inline-Links `[text](ziel)` und Referenzlinks `[text][ref]` mit ihrer Zeilennummer.
  Links innerhalb von Code-Blöcken (``` … ```) und Inline-Code werden nicht extrahiert.
- **FR-02:** Für jeden relativen Link wird geprüft, ob die Zieldatei relativ zur verlinkenden
  Datei existiert. Ein Link, der aus dem geprüften Verzeichnis hinausführt, gilt als Fehler.
- **FR-03:** Enthält ein Link einen Anker (`datei.md#abschnitt` oder nur `#abschnitt`), wird
  geprüft, ob die Zieldatei eine Überschrift mit diesem Slug hat. Slug-Regel wie GitHub:
  Kleinbuchstaben, Leerzeichen → `-`, Satzzeichen außer `-` und `_` entfernt, Duplikate
  bekommen `-1`, `-2`, …
- **FR-04:** Ausgabe als Text (Standard, `datei:zeile: grund`) oder mit `--format json` als
  JSON-Liste `[{"file", "line", "target", "reason"}]`. Exit-Code 0 ohne Befund, 1 mit Befund,
  2 bei Aufruffehlern.
- **FR-05:** Eine optionale Datei `.linkwartignore` im geprüften Verzeichnis enthält Glob-Muster
  (eines je Zeile, `#` leitet Kommentare ein). Passende Linkziele werden nicht gemeldet.

## 5. Nicht-funktionale Anforderungen

- Nur Python-Standardbibliothek (Python ≥ 3.11).
- 400 Dateien in unter 2 Sekunden.
