---
id: SPEC-0048
title: Pattern-Katalog als Kontext – Design-Entscheidungen über Specs hinweg wiederverwenden
type: feature
status: in-progress
owner: Boris
created: 2026-06-23
updated: '2026-06-23'
version: 0.1.0
priority: medium
tags:
- patterns
- design-decisions
- architecture
- llm-integration
- consistency
depends_on:
- SPEC-0015
contracts:
- CON-0182
- CON-0183
tests:
- TST-0210
- TST-0211
fr_test_map:
  FR-01:
  - TST-0210
  FR-02:
  - TST-0210
  FR-03:
  - TST-0211
  FR-04:
  - TST-0211
  FR-05:
  - TST-0211
  FR-06:
  - TST-0210
  FR-07:
  - TST-0211
started_at: '2026-06-23T09:57:38Z'
---
# Pattern-Katalog als Kontext – Design-Entscheidungen über Specs hinweg wiederverwenden

> **Status:** draft · **Owner:** Boris · **Version:** 0.1.0

## 1. Kontext & Motivation

SPEC-0015 hat einen Pattern-Mechanismus eingeführt (`sdd pattern accept/reject`), der akzeptierte
Design-Pattern-Entscheidungen pro Spec unter `.sdd/patterns/<SPEC-ID>-patterns.json` speichert und
zusätzlich in `.sdd/patterns/_catalog.json` projektweit aggregiert (aktuell 10 akzeptierte Patterns
über SPEC-0015, SPEC-0029, SPEC-0034, SPEC-0037).

Dieser Katalog wird jedoch nirgends zurückgelesen:

- `PatternSuggester._build_pattern_prompt()` (`tool/sdd_cli/pattern.py`) baut den LLM-Prompt
  ausschließlich aus dem Text des aktuellen Artefakts. Bereits etablierte Patterns fließen nicht
  ein – das LLM kann pro Spec inkonsistente oder redundante Vorschläge machen (z. B. erneut
  "Observer" mit anderer Begründung vorschlagen, obwohl es in SPEC-0034/0037 bereits für
  Event-Buses etabliert ist).
- `/sdd-implement` Schritt 2 ("Kontext laden") liest nur `.sdd/patterns/$ARGUMENTS-patterns.json`
  – also ausschließlich die Pattern-Entscheidungen der gerade implementierten Spec, nie den
  projektweiten Katalog. Die Implementierung kennt damit keine etablierten Konventionen aus
  anderen Specs.

Das Resultat: Design-Entscheidungen werden zwar dokumentiert, aber nicht wiederverwendet – jedes
neue Feature läuft Gefahr, das Rad neu zu erfinden statt auf bereits getroffene und begründete
Entscheidungen zurückzugreifen.

## 2. Zielsetzung

**Primärziel:** Der globale Pattern-Katalog fließt automatisch als Kontext in Pattern-Vorschläge
(`pattern-suggest`) und in die Implementierungs-Vorbereitung (`/sdd-implement` Schritt 2) ein.

**Erfolgskriterien (messbar):**
- [ ] `PatternRegistry` bietet eine Methode, die den globalen Katalog zu einer kompakten,
  LLM-tauglichen Textzusammenfassung formatiert (Pattern-Name, Spec-ID, Begründung)
- [ ] `_build_pattern_prompt()` bindet diese Zusammenfassung als eigenen Abschnitt ein und
  instruiert das LLM, bei thematischer Nähe bestehende Patterns zu referenzieren statt neue
  vorzuschlagen
- [ ] Ist der Katalog leer oder nicht vorhanden, bleibt der Prompt unverändert (kein leerer
  oder fehlerhafter Abschnitt)
- [ ] `/sdd-implement` Schritt 2 zeigt zusätzlich zur spec-eigenen Pattern-Datei eine
  Zusammenfassung "Etablierte Patterns im Projekt" in der Kontext-Übersicht
- [ ] Der Pattern-Eintrag der aktuell bearbeiteten Spec selbst wird in der Katalog-Zusammenfassung
  nicht dupliziert
- [ ] Bestehende Tests für `pattern.py` (TST-0060–TST-0063) bleiben grün; neue Unit-Tests decken
  die Katalog-Zusammenfassung ab (leer / 1 Eintrag / N Einträge)

**Nicht-Ziele (explizit):**
- Kein Umbau des ADR-Mechanismus (`docs/adr/`)
- Keine Änderung an `sdd pattern accept/reject` (Schreibpfad bleibt unverändert)
- Kein neuer CLI-Befehl zum manuellen Durchsuchen des Katalogs (z. B. `sdd pattern search`)
- Keine Deduplizierung oder Bereinigung des bestehenden Katalog-Inhalts

## 3. Architektur-Entscheidungen & Design Patterns

### 3.1 Template Method Pattern (Behavioral)
**Anwendung:** `_build_pattern_prompt()` definiert bereits eine feste Prompt-Struktur (Instruktion
→ Artefakt-Info → Output-Format). Der neue Katalog-Kontext-Abschnitt wird als zusätzlicher,
optionaler Baustein in dieses feste Skelett eingefügt (`_catalog_context_block(summary)`), ohne
die bestehende Struktur zu verändern.

**Begründung:** Die Prompt-Reihenfolge ist eine Invariante (SPEC-0015 etabliert sie bereits).
Template Method macht den Erweiterungspunkt explizit, ohne den Kern-Aufbau anzufassen (OCP) –
künftige Kontext-Quellen (z. B. ADRs) lassen sich als weiterer Baustein ergänzen.

**Alternative:** Decorator – abgelehnt, weil es hier nicht um Verhalten eines Objekts geht,
sondern um einen festen Textbaustein innerhalb einer bereits bestehenden Funktions-Pipeline;
Decorator würde unnötige Indirektion über eine reine String-Formatierungsfunktion einführen.

Quelle: https://refactoring.guru/design-patterns/template-method

### 3.2 Null Object Pattern (Behavioral)
**Anwendung:** `PatternRegistry.catalog_summary()` gibt bei leerem oder fehlendem Katalog einen
leeren String zurück statt `None`. Aufrufende Stellen (`_build_pattern_prompt`, `/sdd-implement`
Schritt 2) brauchen keinen `if catalog: ...`-Check.

**Begründung:** Dasselbe Pattern wurde bereits in SPEC-0015 für `NullSolidChecker` akzeptiert
(Vermeidung von Existenz-Checks im Aufrufer). Konsistente Wiederverwendung statt erneuter
Ad-hoc-Entscheidung – genau der Fall, den dieses Feature künftig automatisch aufzeigen soll.

**Alternative:** `Optional[str]` mit explizitem `None`-Check an jeder Aufrufstelle – abgelehnt,
weil es den Null-Check dupliziert (an mind. 2 Stellen: Prompt-Builder und Skill-Kontextschritt).

Quelle: https://refactoring.guru/design-patterns/null-object

## 4. Funktionale Anforderungen

- **FR-01:** `PatternRegistry` erhält eine neue Methode `catalog_summary(max_entries: int = 10) -> str`,
  die `_catalog.json` liest und zu einem kompakten Text formatiert (Pattern-Name, Spec-ID, Begründung
  auf 120 Zeichen gekürzt). Kein themenbasierter Filter – immer die jüngsten `max_entries` Einträge.
- **FR-02:** Ist der Katalog leer, nicht vorhanden oder nicht parsebar, liefert `catalog_summary()`
  einen leeren String (Null Object) – kein Fehler, kein Sonderfall im Aufrufer.
- **FR-03:** `_build_pattern_prompt()` erhält einen neuen optionalen Parameter `catalog_context: str`;
  ist er nicht leer, wird er als Abschnitt "BEREITS AKZEPTIERTE PATTERNS IM PROJEKT" vor dem
  Output-Format-Abschnitt eingefügt.
- **FR-04:** Der Prompt-Text instruiert das LLM explizit: bei thematischer Nähe zu einem gelisteten
  Pattern dieses referenzieren/wiederverwenden statt ein neues vorzuschlagen.
- **FR-05:** `PatternSuggester.suggest()` ruft `catalog_summary()` auf und reicht das Ergebnis an
  `_build_pattern_prompt()` durch.
- **FR-06:** Der Pattern-Eintrag der aktuell bearbeiteten Spec/Contract selbst wird aus der
  Katalog-Zusammenfassung ausgeschlossen (kein Duplikat zum bereits separat geladenen Eintrag).
- **FR-07:** `/sdd-implement` Schritt 2 ("Kontext laden") liest zusätzlich zur spec-eigenen
  Pattern-Datei den globalen Katalog und zeigt eine kompakte Zusammenfassung
  "Etablierte Patterns im Projekt: [...]" in der Kontext-Zusammenfassung an.

## 5. User Stories

| ID    | Als ...        | möchte ich ...                                                          | um ...                                                |
|-------|----------------|---------------------------------------------------------------------------|--------------------------------------------------------|
| US-01 | SPEC-Autor     | beim Pattern-Vorschlag sehen, welche Patterns im Projekt bereits etabliert sind | Konsistenz über Specs hinweg zu wahren                 |
| US-02 | KI-Agentin     | beim Implementieren einer neuen Spec etablierte Patterns kennen           | sie wiederzuverwenden statt neu zu erfinden            |
| US-03 | Tech Lead      | sicherstellen, dass neue Pattern-Vorschläge bestehenden nicht widersprechen | Architektur-Drift über Specs hinweg zu vermeiden       |

## 6. Contracts

| ID | Typ | Titel |
|----|-----|-------|
| CON-0182 | behavior | Pattern-Katalog-Kontext – Verhalten bei Prompt-Aufbau und Skill-Kontextladen |
| CON-0183 | data | `PatternRegistry.catalog_summary()` – Ausgabeformat |

## 7. Tests

| ID | Level | Contract | Titel |
|----|-------|----------|-------|
| TST-0210 | unit | CON-0183 | `PatternRegistry.catalog_summary()` – Ausgabeformat |
| TST-0211 | unit | CON-0182 | Pattern-Katalog-Kontext – Prompt-Aufbau und Skill-Kontextladen |

## 8. Implementierungsreihenfolge

1. `PatternRegistry.catalog_summary()` implementieren + Unit-Tests (leer / 1 Eintrag / N Einträge,
   eigene Spec ausgeschlossen)
2. `_build_pattern_prompt()` um optionalen `catalog_context`-Parameter erweitern (Template-Method-
   Baustein), bestehende Tests müssen weiter grün bleiben
3. `PatternSuggester.suggest()` verdrahten
4. `.claude/commands/sdd-implement.md` Schritt 2 um Katalog-Ladeschritt erweitern
5. `.claude/commands/sdd-review.md` Schritt 3 (Pattern-Vorschläge) ggf. Hinweistext ergänzen,
   dass Katalog-Kontext jetzt einfließt

## 9. Offene Fragen

| # | Frage | Verantwortlich | Deadline |
|---|-------|----------------|----------|
| OQ-01 | ✅ Soll die Katalog-Zusammenfassung nach Themennähe gefiltert werden oder immer der vollständige Katalog eingebunden werden? **Antwort:** Immer vollständig (kein Filter-Mechanismus in v0.1.0; bei Bedarf später nachrüstbar). | Boris | geklärt |
| OQ-02 | ✅ Gibt es eine harte Obergrenze für Anzahl/Zeichenlänge der eingebetteten Katalog-Einträge? **Antwort:** Ja – `max_entries=10` (siehe FR-01), Begründungstext pro Eintrag auf 120 Zeichen gekürzt. | Boris | geklärt |

## 10. Änderungshistorie

| Version | Datum      | Änderung           |
|---------|------------|---------------------|
| 0.1.0   | 2026-06-23 | Initiale Erstellung |
