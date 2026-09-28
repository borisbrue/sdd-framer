---
id: SPEC-0049
title: Pattern-Nutzung in der UI – akzeptierte Design-Patterns mit Code-Fundstellen
  anzeigen
type: feature
status: implemented
owner: Boris
created: 2026-06-23
updated: '2026-06-23'
version: 0.1.0
priority: medium
tags:
- patterns
- ui
- web
- architecture
- visibility
depends_on:
- SPEC-0015
- SPEC-0048
contracts:
- CON-0184
- CON-0185
tests:
- TST-0216
- TST-0217
- TST-0218
fr_test_map:
  FR-01:
  - TST-0216
  FR-02:
  - TST-0217
  FR-03:
  - TST-0217
  FR-04:
  - TST-0217
  FR-05:
  - TST-0217
  FR-06:
  - TST-0218
started_at: '2026-06-23T20:42:54Z'
---
# Pattern-Nutzung in der UI – akzeptierte Design-Patterns mit Code-Fundstellen anzeigen

> **Status:** draft · **Owner:** Boris · **Version:** 0.1.0

## 1. Kontext & Motivation

SPEC-0015 hat einen Pattern-Mechanismus eingeführt, der akzeptierte Design-Pattern-Entscheidungen
pro Spec unter `.sdd/patterns/<SPEC-ID>-patterns.json` speichert und projektweit in
`.sdd/patterns/_catalog.json` aggregiert. SPEC-0048 nutzt diesen Katalog bereits als LLM-Kontext.

Parallel dazu annotiert der Quellcode Patterns konsequent im Docstring/Kommentar – aktuell in
**26 Dateien** unter `tool/sdd_cli/` (z. B. `Observer Pattern:`, `State Pattern:`,
`Strategy Pattern (Refactoring Guru):`, `Mediator Pattern:`, `Facade Pattern:`).

Beide Informationsquellen – der kuratierte Katalog (warum ein Pattern gewählt wurde) und die
Code-Annotationen (wo es tatsächlich umgesetzt ist) – sind heute jedoch nur über CLI/JSON bzw.
über `grep` im Code sichtbar. Die Web-UI bietet **keinen** Zugang:

- Kein Pattern-Endpunkt in `web/api/routes/`.
- Keine Pattern-Komponente in `web/ui/src/`.

Damit bleibt die getroffene und begründete Architektur-Entscheidung für Entwickler:innen und
Reviewer:innen unsichtbar, solange sie nicht aktiv in die JSON-Dateien oder den Code schauen.

## 2. Zielsetzung

**Primärziel:** Eine globale, read-only **„Patterns"-Ansicht** in der Web-UI, die die *tatsächlich
verwendeten* (akzeptierten) Design-Patterns des Projekts zeigt – mit Begründung, Refactoring-Guru-Link
und konkreten Code-Fundstellen.

**Erfolgskriterien (messbar):**
- [ ] `GET /api/patterns` liefert für jedes akzeptierte Pattern: Name, nutzende Specs (mit Begründung),
  `refactoring_guru_url` und `code_locations` (Datei + Zeile + Annotationszeile).
- [ ] Ein neuer Nav-Eintrag „Patterns" rendert eine View, die je Pattern eine Karte zeigt.
- [ ] Der Code-Scanner findet die im Code annotierten Patterns wieder (mindestens die in `tool/sdd_cli/`
  vorhandenen: Observer, State, Strategy, Mediator, Decorator, Facade, Builder).
- [ ] Ein akzeptiertes Pattern ohne Code-Fundstelle erscheint trotzdem (mit leerer Fundstellenliste).
- [ ] `suggested`- und `rejected`-Patterns erscheinen NICHT in der Ansicht.
- [ ] Ist der Katalog leer, zeigt die View einen freundlichen Leer-Zustand statt eines Fehlers.
- [ ] Unit-Tests decken ab: Scanner-Matching inkl. Namens-Normalisierung, Merge (mit/ohne Fundstelle),
  leere Katalog-Quelle.

**Nicht-Ziele (explizit):**
- Keine `suggested`/`rejected`-Patterns – nur `accepted` (verwendete).
- Kein Editieren/Akzeptieren/Ablehnen von Patterns in der UI – die Ansicht ist read-only.
- **Keine AST- oder semantische Pattern-Erkennung** – ausschließlich Annotationsscan auf
  `<PatternName> Pattern` in Kommentaren/Docstrings.
- Kein Pattern-Abschnitt in `SpecDetail` – bewusst nur die globale Übersicht.
- Keine Änderung am Schreibpfad (`PatternRegistry.accept/reject`) oder am Katalog-Inhalt.

## 3. Architektur-Entscheidungen & Design Patterns

### 3.1 Strategy Pattern (Behavioral)
**Anwendung:** Zwei Pattern-Quellen – ein `CatalogPatternSource` (liest `_catalog.json` über die
bestehende `PatternRegistry`) und ein `CodeAnnotationScanner` (scant die Source-Roots) – implementieren
ein gemeinsames `PatternSource`-Protocol. Der Aggregator iteriert über austauschbare Quellen.

**Begründung:** Eine künftige, präzisere Quelle (AST-basiert, oder ADR-Referenzen) lässt sich als
weitere Strategy andocken, ohne Aggregator, Route oder UI zu ändern (OCP). Quellen sind isoliert
unit-testbar. Konsistent mit der etablierten Strategy-Nutzung in `routing.py` und `llm_probe.py`.

**Alternative:** Eine monolithische Funktion, die Katalog-Lesen und Code-Scan fest verdrahtet –
abgelehnt, weil sie OCP verletzt und das isolierte Testen der Quellen erschwert.

Quelle: https://refactoring.guru/design-patterns/strategy

### 3.2 Facade Pattern (Structural)
**Anwendung:** Ein `PatternUsageService.usage() -> list[PatternUsage]` kapselt das Zusammenspiel von
Quellen + Merge hinter einer Methode. Die Route `patterns.py` und die UI kennen nur die Fassade,
nicht Katalog-Reader, Scanner oder Merge-Logik.

**Begründung:** Hält die HTTP-Route dünn (SRP) und schützt API/UI vor interner Umstrukturierung.
Konsistent mit dem `Facade Pattern` in `dev_container.py` (`DevContainerManager`).

**Alternative:** Die Route ruft Reader + Scanner direkt auf und merged inline – abgelehnt, weil
Aggregations-Logik in der HTTP-Schicht landet und schlecht testbar ist.

Quelle: https://refactoring.guru/design-patterns/facade

### 3.3 Wiederverwendung statt Neubau (SOLID/DRY)
Der Katalogzugriff erfolgt über die bestehende `PatternRegistry` (`_load_catalog`/`catalog_summary`),
**kein** zweiter JSON-Leser. Auf der UI-Seite werden bestehende Komponenten wiederverwendet:
`IdChip` für Spec-Referenzen, `OpenButton` für klickbare Code-Fundstellen, `AiUsageView.tsx` als
strukturelle Vorlage für die read-only View.

## 4. Funktionale Anforderungen

- **FR-01:** Neuer API-Endpunkt `GET /api/patterns` liefert akzeptierte Patterns aggregiert:
  `[{pattern_name, specs:[{spec_id, reason}], refactoring_guru_url, code_locations:[{file, line, annotation}]}]`.
- **FR-02:** Die Katalog-Quelle liest `accepted_patterns` aus `_catalog.json` über die bestehende
  `PatternRegistry` und gruppiert nach `pattern_name` (mehrere Specs pro Pattern werden gebündelt).
- **FR-03:** Der Code-Annotation-Scanner durchsucht die Source-Roots (Default `tool/sdd_cli/` und
  `web/`; optional über `patterns.scan_roots` in `config.yaml` überschreibbar) nach
  `<PatternName> Pattern`-Annotationen in Kommentaren/Docstrings und liefert je Fund den
  repo-relativen Pfad, die Zeilennummer und die Annotationszeile.
- **FR-04:** Das Matching zwischen Code-Annotation und Katalog-Pattern ist
  normalisiert (Leerzeichen entfernt + lowercase), sodass z. B. `ChainOfResponsibility` und
  `Chain of Responsibility` zusammenfallen. Eine explizite Alias-Tabelle ist nicht Teil von v0.1.0.
- **FR-05:** Der Merge ordnet Fundstellen den Katalog-Patterns zu. Akzeptierte Patterns **ohne**
  Fundstelle erscheinen mit leerer `code_locations`-Liste. Code-Fundstellen **ohne** Katalogeintrag
  werden ignoriert (es werden nur akzeptierte Patterns gezeigt).
- **FR-06:** Die UI erhält einen Nav-Eintrag „Patterns" und eine read-only View: je Pattern eine
  Karte mit Name, nutzenden Specs (über `IdChip`), externem Guru-Link und einer Liste der
  Code-Fundstellen, die per `OpenButton` im Editor geöffnet werden können. Bei leerem Katalog wird
  ein freundlicher Leer-Zustand angezeigt.

## 5. User Stories

| ID    | Als ...        | möchte ich ...                                                          | um ...                                                |
|-------|----------------|---------------------------------------------------------------------------|--------------------------------------------------------|
| US-01 | Entwickler:in  | auf einen Blick sehen, welche Patterns das Projekt verwendet und wo im Code | Konsistenz zu wahren und Vorhandenes wiederzuverwenden |
| US-02 | Reviewer:in    | Begründung und Refactoring-Guru-Referenz eines Patterns sehen             | Architektur-Entscheidungen nachzuvollziehen            |
| US-03 | Neue:r im Team | von der Pattern-Karte direkt zur Code-Fundstelle springen                 | die Umsetzung schnell zu verstehen                     |

## 6. Contracts

> Werden im Schritt `/sdd-review SPEC-0049` → Contract-Erstellung ergänzt (API-Shape für
> `GET /api/patterns`, Verhalten des Scanners/Merges).

## 7. Tests

> Werden nach Contract-Approval ergänzt (Scanner-Matching/Normalisierung, Merge mit/ohne
> Fundstelle, leere Katalog-Quelle, Endpunkt-Shape).

## 8. Implementierungsreihenfolge

1. `pattern_usage.py`: `PatternSource`-Protocol + `CatalogPatternSource` (über `PatternRegistry`)
   + `CodeAnnotationScanner` (Source-Roots, Normalisierung) inkl. Unit-Tests.
2. `PatternUsageService` (Facade) – Quellen aggregieren + mergen, Unit-Tests (mit/ohne Fundstelle,
   leerer Katalog).
3. Route `web/api/routes/patterns.py` – `GET /api/patterns`, registrieren in der App.
4. UI – `api.ts` Client-Funktion, `PatternsView`-Komponente (Vorlage `AiUsageView.tsx`),
   Nav-Eintrag „Patterns".

## 9. Offene Fragen

| # | Frage | Verantwortlich | Deadline |
|---|-------|----------------|----------|
| OQ-01 | ✅ Welche Source-Roots scannt der Code-Scanner? **Antwort:** Default `tool/sdd_cli/` + `web/`, optional über `patterns.scan_roots` in `config.yaml` überschreibbar (siehe FR-03). | Boris | geklärt |
| OQ-02 | ✅ Sollen Code-Fundstellen klickbar sein? **Antwort:** Ja – im Editor öffnen über die bestehende `OpenButton`-Komponente (siehe FR-06). | Boris | geklärt |
| OQ-03 | ✅ Wie werden Pattern-Namen zwischen Code und Katalog abgeglichen? **Antwort:** Normalisierung (Leerzeichen entfernt + lowercase); keine Alias-Tabelle in v0.1.0 (siehe FR-04). | Boris | geklärt |

## 10. Änderungshistorie

| Version | Datum      | Änderung           |
|---------|------------|---------------------|
| 0.1.0   | 2026-06-23 | Initiale Erstellung |
