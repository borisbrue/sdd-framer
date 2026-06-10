---
id: SPEC-0047
title: Vision Stats – Statistiken zur aktuellen Vision
type: feature
status: in-progress
owner: Boris
created: 2026-06-10
updated: '2026-06-10'
version: 0.1.0
priority: medium
tags:
- vision
- stats
- cli
depends_on:
- SPEC-0046
contracts:
- CON-0180
- CON-0181
tests:
- TST-0206
- TST-0207
fr_test_map:
  FR-01:
  - TST-0207
  FR-02:
  - TST-0206
  FR-03:
  - TST-0206
started_at: '2026-06-10T20:18:08Z'
---
# Vision Stats – Statistiken zur aktuellen Vision

> **Status:** draft · **Owner:** Boris · **Version:** 0.1.0

## 1. Kontext & Motivation

Nach `sdd vision init` und mehreren `sdd vision add-feature`-Aufrufen hat der
Solo-Entwickler keine schnelle Übersicht: Wie viele Features gibt es? Wie viele
Tasks sind erledigt? Wie viele Features wurden bereits gechallengt?

`sdd vision stats` schließt diese Lücke mit einer einzeiligen Ausgabe pro
Kategorie — kein Parsen, kein Öffnen der Datei.

## 2. Zielsetzung

**Primärziel:**
Einen schnellen, maschinenlesbaren Überblick über den Zustand der
`.sdd/vision.md` auf einen Blick liefern.

**Erfolgskriterien (messbar):**
- [ ] `sdd vision stats` gibt Feature-Anzahl aus
- [ ] Gibt Tasks gesamt, done und offen aus
- [ ] Gibt Anzahl der Features mit LLM-Challenge aus
- [ ] Gibt Anzahl der Features mit Code-Challenge aus
- [ ] Exit-Code 0 bei vorhandener vision.md, ≠ 0 wenn sie fehlt

**Nicht-Ziele (explizit):**
- Kein Export in andere Formate (JSON, CSV, kein `--json` Flag)
- Kein historischer Vergleich über Zeit
- Kein Traceability-Gate zu Specs/Contracts

## 3. User Stories

| ID    | Als …           | möchte ich …                                     | um …                                              |
|-------|-----------------|--------------------------------------------------|---------------------------------------------------|
| US-01 | Solo-Entwickler | `sdd vision stats` aufrufen                      | schnell den Projektstatus zu überblicken          |
| US-02 | Solo-Entwickler | sehen wie viele Features noch nicht gechallengt sind | zu entscheiden welche als nächstes challengen |

## 4. Funktionale Anforderungen

- **FR-01 – Stats berechnen:**
  Liest `.sdd/vision.md` via `VisionDocument.from_file()` (SPEC-0046).
  Berechnet aus den geparsten Daten: Feature-Anzahl, Task-Anzahl (gesamt / done /
  offen), LLM-Challenge-Count (Features mit `llm_challenge is not None`),
  Code-Challenge-Count (Features mit `code_challenge is not None`).

- **FR-02 – Ausgabe:**
  Gibt die Statistiken formatiert auf stdout aus. Mindestformat:
  ```
  Features:        3
  Tasks:           5  (done: 2 / offen: 3)
  LLM Challenges:  1
  Code Challenges: 2
  ```
  Exit-Code 0.

- **FR-03 – Fehlverhalten:**
  Existiert `.sdd/vision.md` nicht, gibt der Befehl eine lesbare Fehlermeldung
  aus (mit Hinweis auf `sdd vision init`) und beendet sich mit Exit-Code ≠ 0.

## 5. Architektur & Design Patterns

### Value Object Pattern
**Begründung:** Die berechneten Statistiken sind unveränderliche, rein datengetriebene
Werte ohne Identität. Ein `VisionStats`-Dataclass fasst alle Kennzahlen in einem
Objekt zusammen — leicht testbar, keine Seiteneffekte.
[Refactoring Guru – Value Object](https://refactoring.guru/design-patterns/value-objects)

### Facade Pattern
**Begründung:** `sdd vision stats` ist die einzige Einstiegsstelle und verbirgt
VisionDocument-Parsing, Statistik-Berechnung und Ausgabe hinter einem CLI-Befehl.
Kein Aufrufer muss wissen wie die Berechnung intern funktioniert.
[Refactoring Guru – Facade](https://refactoring.guru/design-patterns/facade)

## 6. Contracts

*(werden nach Spec-Approval ergänzt)*

## 7. Tests

*(werden nach Contract-Approval ergänzt)*

## 8. Offene Fragen

- [x] Soll die Ausgabe auch maschinell lesbar sein (z.B. `--json` Flag)? → Nein, kein `--json`. Rein menschenlesbare Ausgabe.

## 9. Implementierungsreihenfolge

1. `VisionStats` Value Object (Dataclass mit Feldern + `from_document()` Klassenmethode)
2. `sdd vision stats` CLI-Befehl (Facade, nutzt VisionDocument + VisionStats)

## 10. Änderungshistorie

| Datum      | Version | Autor  | Änderung            |
|------------|---------|--------|---------------------|
| 2026-06-10 | 0.1.0   | Boris  | Initiale Erstellung |
