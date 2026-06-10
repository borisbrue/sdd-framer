---
id: SPEC-0046
title: Vision Edition – Interaktive Produktvision & Feature-Exploration
type: feature
status: in-progress
owner: Boris
created: 2026-06-10
updated: '2026-06-10'
version: 0.1.2
priority: medium
tags:
- vision
- planning
- feature-exploration
- interactive
depends_on:
- SPEC-0008
- SPEC-0016
contracts:
- CON-0175
- CON-0176
- CON-0177
- CON-0178
- CON-0179
tests:
- TST-0201
- TST-0202
- TST-0203
- TST-0204
- TST-0205
fr_test_map:
  FR-01:
  - TST-0201
  FR-02:
  - TST-0202
  FR-03:
  - TST-0203
  FR-04:
  - TST-0204
  FR-05:
  - TST-0204
  FR-05a:
  - TST-0204
  FR-06:
  - TST-0203
started_at: '2026-06-10T15:33:48Z'
---
# Vision Edition – Interaktive Produktvision & Feature-Exploration

> **Status:** draft · **Owner:** Boris · **Version:** 0.1.0

## 1. Kontext & Motivation

SDD-Framer beginnt heute direkt auf Spec-Ebene. Es gibt keinen strukturierten
Ort, um vor der ersten Spec zu verstehen: Was soll das Produkt können? Welchen
Tech-Stack nutzen wir? Wer sind die Mitbewerber? Wie grenzen wir uns ab?

Solo-Entwickler und kleine Teams denken Produkte oft iterativ und kreativ —
Ideen entstehen spontan, werden verworfen, reifen über Zeit. Dieser Prozess
passt nicht in das Spec-Format, das Klarheit und Vollständigkeit voraussetzt.

Die Vision Edition schafft eine vorgelagerte Ebene: einen lebendigen, informellen
Raum für Produktdenken. Pro Projekt existiert genau eine Vision — sie entsteht
optional im `sdd init`-Prozess und kann jederzeit weiterentwickelt werden.
Feature-Ideen können grob festgehalten und gegen das LLM sowie den bestehenden
Code gechallengt werden, um ein Gefühl für Aufwand und Komplexität zu entwickeln,
bevor die Entscheidung für einen Spec fällt.

## 2. Zielsetzung

**Primärziel:**
Einen strukturierten, aber kreativen Planungsraum schaffen, der zwischen
"Produktidee" und "Spec-ready" liegt — als ein einziges lebendiges Dokument
pro Projekt.

**Erfolgskriterien (messbar):**
- [ ] `.sdd/vision.md` kann über `sdd init` oder `sdd vision init` erstellt werden
- [ ] Feature-Ideen können ohne vollständige Ausarbeitung zur Vision hinzugefügt werden
- [ ] Jede Feature-Idee kann gegen das LLM gechallengt werden und liefert eine
      Aufwandseinschätzung (low / medium / high / unknown) mit Begründung
- [ ] Jede Feature-Idee kann gegen den bestehenden Code gechallengt werden und
      liefert eine Liste betroffener Dateien/Module
- [ ] Einfache Tasks können direkt in der Vision erfasst werden

**Nicht-Ziele (explizit):**
- Kein automatisches Ableiten von ausführbaren Entwicklungs-Tasks oder Specs
- Kein Ersetzen des Spec-Prozesses — Vision ist Vorstufe, nicht Ersatz
- Keine Traceability-Gates oder Haltbarkeitsgarantien für Vision-Inhalte
- Mehrere Visionen pro Projekt — es gibt genau eine

## 3. User Stories

| ID    | Als …           | möchte ich …                                                          | um …                                                      |
|-------|-----------------|-----------------------------------------------------------------------|-----------------------------------------------------------|
| US-01 | Solo-Entwickler | beim `sdd init` optional eine Produktvision anlegen                   | von Anfang an einen Planungsrahmen zu haben               |
| US-02 | Entwickler      | Feature-Ideen grob festhalten ohne sie vollständig auszuarbeiten      | den kreativen Fluss nicht zu unterbrechen                 |
| US-03 | Entwickler      | eine Feature-Idee gegen das LLM challengen                            | ein Gefühl für Aufwand und Komplexität zu bekommen        |
| US-04 | Entwickler      | eine Feature-Idee gegen den bestehenden Code challengen               | zu verstehen welche Teile der Codebase betroffen wären    |
| US-05 | Solo-Entwickler | einfache Tasks direkt in der Vision notieren                          | nichts zu vergessen ohne gleich einen Spec aufzumachen    |
| US-06 | Entwickler      | die Vision jederzeit anzeigen und bearbeiten                          | sie als lebendes Dokument pflegen zu können               |

## 4. Funktionale Anforderungen

- **FR-01 – Vision initialisieren:**
  `sdd vision init` erstellt `.sdd/vision.md`. Interaktiver Wizard befüllt:
  Vision Statement, Zielgruppe, Tech Stack, Competitive Landscape, Kernprobleme.
  Alle Felder optional — ein Skelett-Dokument ist gültig.
  Existiert `.sdd/vision.md` bereits, bricht der Befehl mit Hinweis ab.
  `sdd init` bietet den Vision-Schritt als optionalen Schritt an — der Nutzer
  kann ihn überspringen; das Projekt ist ohne Vision vollständig funktionsfähig.

- **FR-02 – Vision anzeigen und editieren:**
  `sdd vision show` gibt das vollständige Vision-Dokument formatiert aus.
  `sdd vision edit` öffnet `.sdd/vision.md` im konfigurierten Editor
  (`$EDITOR`, Fallback: direktes Ausgeben des Pfads).

- **FR-03 – Feature-Ideen erfassen:**
  `sdd vision add-feature` erfasst interaktiv: Titel + ein Satz Beschreibung.
  Keine Contracts, keine Tests, kein Status-Lifecycle. Features werden als
  nummerierte Liste im Vision-Dokument unter `## Features` geführt.

- **FR-04 – LLM Challenge:**
  `sdd vision challenge <feature-index> --llm` sendet die Feature-Beschreibung
  zusammen mit dem Vision-Kontext an den LLM-Provider.
  Der Aufruf erfolgt ausschließlich über die in SPEC-0008 definierte
  `AIProvider`-Abstraktionsschicht (`ai_routes`-Interface) — kein direkter
  Provider-Zugriff. Die Challenge läuft als Hintergrundjob (async, gemäß
  SPEC-0016) und gibt Fortschritt auf stdout aus; das Ergebnis steht nach
  Abschluss zur Verfügung.
  Rückgabe: Aufwand (low/medium/high/unknown), Begründung, mögliche Fallstricke.
  Ergebnis wird inline unter dem Feature-Eintrag als `> LLM Challenge:` gespeichert.

- **FR-05 – Code Challenge:**
  `sdd vision challenge <feature-index> --code` durchsucht den Projektcode
  via Keyword-Matching (Feature-Titel + Schlüsselwörter aus der Beschreibung).
  Die Code-Analyse läuft synchron (kein LLM-Aufruf), ist also von SPEC-0016
  nicht betroffen.
  Ausgabe: Liste betroffener Dateien, grobe Einschätzung des Änderungsumfangs.
  Ergebnis wird inline unter dem Feature-Eintrag als `> Code Challenge:` gespeichert.

- **FR-05a – Kombinierter Challenge (Default):**
  `sdd vision challenge <feature-index>` ohne Flag führt LLM Challenge und
  Code Challenge sequenziell aus und gibt beide Ergebnisse zusammen aus.
  `--llm` und `--code` sind explizite Flags für gezielte Einzelausführung.
  Der kombinierte Aufruf startet den LLM-Job async und führt die Code-Analyse
  synchron parallel aus; beide Ergebnisse werden nach Abschluss zusammen angezeigt.

- **FR-06 – Simple Tasks:**
  `sdd vision add-task` erfasst: Titel + optionale Beschreibung.
  Tasks werden unter `## Tasks` im Vision-Dokument als Checkbox-Liste geführt.
  Kein Lifecycle, keine Contracts — reine Notizen.

## 5. Architektur & Design Patterns

### Builder Pattern
**Begründung:** Das Vision-Dokument wird Abschnitt für Abschnitt aufgebaut.
Jeder Schritt im interaktiven Wizard fügt einen weiteren Block hinzu.
Der Builder trennt den Konstruktionsprozess vom fertigen Dokument — neue
Abschnitte können ergänzt werden ohne den Wizard-Flow zu brechen.
[Refactoring Guru – Builder](https://refactoring.guru/design-patterns/builder)

### Strategy Pattern
**Begründung:** Der Challenge-Mechanismus hat zwei austauschbare Strategien:
`LLMChallengeStrategy` und `CodeChallengeStrategy`. Beide implementieren
dasselbe `ChallengeStrategy`-Interface (`challenge(feature, context) → ChallengeResult`).
Weitere Strategien (z.B. Competitor-Check) können ohne Änderung am CLI ergänzt werden.
`LLMChallengeStrategy` nutzt intern ausschließlich das `AIProvider`-Interface
aus SPEC-0008 — der konkrete Provider ist austauschbar und nicht hart-codiert.
[Refactoring Guru – Strategy](https://refactoring.guru/design-patterns/strategy)

### Facade Pattern
**Begründung:** `sdd vision challenge` orchestriert intern LLM-Aufruf, Code-Analyse
und Ergebnis-Persistenz in `.sdd/vision.md`. Die Facade verbirgt diese Komplexität
hinter einem einzigen CLI-Befehl.
[Refactoring Guru – Facade](https://refactoring.guru/design-patterns/facade)

## 6. Contracts (was wird garantiert)

*(werden nach Spec-Approval ergänzt)*

## 7. Tests (wie wird verifiziert)

*(werden nach Contract-Approval ergänzt)*

## 8. Offene Fragen

- [x] Soll `sdd init` die Vision als verpflichtenden oder optionalen Schritt einbauen?
      → Optional. Projekt ist ohne Vision vollständig funktionsfähig.
- [x] Soll `sdd vision challenge` beide Strategien kombiniert anbieten?
      → Ja. Kein Flag = LLM + Code laufen beide. `--llm` / `--code` für gezielte Einzelausführung.

## 9. Implementierungsreihenfolge

1. `.sdd/vision.md`-Format definieren (Markdown-Struktur mit fixen Abschnitten)
2. `sdd vision init` — interaktiver Wizard (Builder)
3. `sdd vision show` + `sdd vision edit`
4. `sdd vision add-feature` + `sdd vision add-task`
5. `LLMChallengeStrategy` + `CodeChallengeStrategy` (Strategy)
6. `sdd vision challenge` CLI-Befehl (Facade)
7. Challenge-Ergebnisse inline in `.sdd/vision.md` persistieren
8. Optionaler Vision-Schritt in `sdd init` integrieren

## 10. Änderungshistorie

| Datum      | Version | Autor  | Änderung            |
|------------|---------|--------|---------------------|
| 2026-06-10 | 0.1.0   | Boris  | Initiale Erstellung |
| 2026-06-10 | 0.1.1   | Boris  | Offene Fragen geklärt: Vision-Schritt in init optional; challenge ohne Flag = LLM + Code kombiniert |
| 2026-06-10 | 0.1.2   | Claude | Regression-Fixes: depends_on SPEC-0008; FR-04 an AIProvider-Abstraktionsschicht gebunden; LLM-Challenge async per SPEC-0016; Code-Challenge explizit sync |
