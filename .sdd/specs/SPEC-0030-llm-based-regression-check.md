---
id: SPEC-0030
title: LLM-Based Regression Check
type: feature
status: in-progress
owner: Boris
created: 2026-05-30
updated: '2026-05-29'
version: 0.1.0
priority: medium
tags: []
depends_on: []
contracts: []
tests: []
adrs: []
started_at: '2026-05-29T23:32:46Z'
---
# LLM-Based Regression Check

> **Status:** draft · **Owner:** Boris · **Version:** 0.1.0

## 1. Kontext & Motivation

`sdd regression-check` (eingeführt in SPEC-0029) prüft eine Spec regelbasiert
auf Konflikte mit bestehenden, implementierten Specs — Endpoint-Konflikte,
Lifecycle-Konflikte, Schema-Konflikte. Diese Stufe ist deterministisch, aber
blind gegenüber semantischen Überschneidungen: zwei Specs können unterschiedliche
Feldnamen nutzen, dasselbe inhaltliche Problem aber doppelt lösen.

Ziel dieser Spec ist ein ergänzender **LLM-basierter Semantik-Check**, der den
Spec-Inhalt (Kontext, Anforderungen, User Stories) mit bestehenden Specs
vergleicht und inhaltliche Überschneidungen mit konkreten Fundstellen meldet.
Der regelbasierte Check aus SPEC-0029 bleibt unverändert bestehen.

## 2. Zielsetzung

**Primärziel:**
Inhaltliche Überschneidungen zwischen Specs werden vom LLM erkannt und mit
konkreten Fundstellen (SPEC-ID, Abschnitt, FR-ID) gemeldet — als eigenständige
Stufe 2 innerhalb von `sdd regression-check`.

**Erfolgskriterien (messbar):**

- [ ] LLM-Check erkennt semantische Überschneidungen und gibt Fundstellen aus
      (mind. SPEC-ID + betroffener Abschnitt/FR-ID)
- [ ] Jeder Befund enthält Severity (`error` / `warning` / `info`) und eine
      konkrete Beschreibung der Überschneidung
- [ ] Bei 0 Befunden erscheint `✓ Kein inhaltlicher Regressionskonflikt gefunden`
- [ ] Der regelbasierte Check (Stufe 1) wird nicht verändert und läuft weiterhin

**Nicht-Ziele (explizit):**

- Ersetzen oder Verändern des regelbasierten Checks aus SPEC-0029
- Automatisches Zusammenführen oder Anpassen von Specs
- Embedding-basierte Vektordatenbank / Retrieval-Infrastruktur
- Prüfung von Contracts oder Tests (nur Spec-Dokumente)

## 3. Architektur & Design Patterns

### Pattern 1 — Chain of Responsibility
**Zweck:** Regelbasierter Check (Stufe 1) und LLM-Check (Stufe 2) sind
unabhängige Handler in einer Prüfkette. Jeder Handler entscheidet selbst, ob er
eine Fundstelle meldet; die Kette kann erweitert werden ohne bestehende Handler
zu ändern.

**Refactoring Guru:** https://refactoring.guru/design-patterns/chain-of-responsibility

```
RegressionCheckChain
  ├── RuleBasedCheckHandler  (Stufe 1, deterministisch)
  └── LLMSemanticCheckHandler  (Stufe 2, inhaltlich)
```

### Pattern 2 — Strategy
**Zweck:** Die LLM-Prüfstrategie (Prompt-Aufbau, Vergleichstiefe, Modell) ist
austauschbar, ohne den äußeren `sdd regression-check`-Flow zu ändern.
Konkrete Strategien: `FullContentStrategy` (ganzer Spec-Text),
`SectionBySection` (abschnittsweise), `RequirementsPairwise` (FR-zu-FR).

**Refactoring Guru:** https://refactoring.guru/design-patterns/strategy

```
LLMSemanticCheckHandler
  └── uses → SemanticCheckStrategy
               ├── FullContentStrategy     (default)
               └── RequirementsPairwise    (--deep)
```

## 4. Funktionale Anforderungen

- **FR-01:** `sdd regression-check SPEC-XXXX` führt nach dem regelbasierten
  Check automatisch den LLM-Semantik-Check durch (Stufe 2). Kein separates Flag
  notwendig; das Verhalten ist Standard.
- **FR-02:** Der LLM-Check lädt als Kontext: die vollständige Ziel-Spec +
  alle Specs mit `status: implemented` (oder `in-progress`). Specs im Status
  `draft` werden übersprungen.
- **FR-03:** Das LLM gibt seine Befunde strukturiert zurück:
  - `spec_id`: betroffene Gegenseite (z.B. `SPEC-0005`)
  - `section`: betroffener Abschnitt in der Gegenseite (z.B. `FR-03`)
  - `own_section`: betroffener Abschnitt in der Ziel-Spec (z.B. `FR-02`)
  - `type`: `overlap` / `conflict` / `redundancy`
  - `severity`: `error` / `warning` / `info`
  - `description`: ein konkreter Satz der die Überschneidung benennt
- **FR-04:** Die Ausgabe von `sdd regression-check` zeigt Stufe-1- und
  Stufe-2-Befunde getrennt, mit eindeutiger Kennzeichnung
  (`[rule]` vs. `[llm]`).
- **FR-05:** Bei `severity: error` endet `sdd regression-check` mit Exit-Code 1.
  Bei nur `warning`/`info`: Exit-Code 0 mit Hinweis.
- **FR-06:** Ist kein LLM-Aufruf möglich (API nicht erreichbar, kein Key),
  wird Stufe 2 mit Warnung übersprungen: `⚠ LLM-Check übersprungen (kein API-Zugang)`.
  Die Stufe-1-Ergebnisse werden normal ausgegeben.
- **FR-07:** `/sdd-review` ruft `sdd regression-check SPEC-XXXX` auf und zeigt
  beide Stufen als eigenen Review-Schritt (keine Änderung am Skill-Interface,
  nur die Ausgabe ist nun zweistufig).

## 5. User Stories

| ID    | Als ...    | möchte ich ...                                                    | um ...                                                              |
| ----- | ---------- | ----------------------------------------------------------------- | ------------------------------------------------------------------- |
| US-01 | CLI-Nutzer | beim `/sdd-review` automatisch einen LLM-Semantik-Check erhalten  | inhaltliche Dopplungen zu anderen Specs früh zu erkennen            |
| US-02 | CLI-Nutzer | konkrete Fundstellen (SPEC-ID + Abschnitt) in den Befunden lesen  | gezielt nachschauen wo genau die Überschneidung liegt               |
| US-03 | CLI-Nutzer | `/sdd-validate` auch mit LLM-Check ausführen können               | die Spec vor dem Approve auf inhaltliche Konflikte zu prüfen        |
| US-04 | Entwickler | den LLM-Check ohne Unterbrechung des regelbasierten Checks nutzen | beide Prüfstufen in einem einzigen Kommando zu erhalten             |

## 6. Contracts

*(werden in `/sdd-new contract` ergänzt)*

## 7. Tests

*(werden in `/sdd-new test` ergänzt)*

## 8. Implementierungsreihenfolge

1. LLM-Prompt-Design: Prompt-Template für semantischen Spec-Vergleich (Stufe 2)
2. `SemanticCheckStrategy` implementieren (FullContent als Default)
3. `LLMSemanticCheckHandler` in `RegressionCheckChain` einhängen
4. Ausgabe-Format (getrennte `[rule]` / `[llm]` Sektionen) implementieren
5. Fehlerbehandlung bei nicht verfügbarem LLM (FR-06)
6. `/sdd-review`-Skill auf zweistufige Ausgabe anpassen (FR-07)

## 9. Offene Fragen

- [x] Welches Modell wird für den LLM-Check verwendet? (Default: claude-sonnet)
    Ja, das passt, sollte aber konfigurierbar sein.
- [x] Gibt es ein Token-Limit-Problem wenn viele implementierte Specs verglichen werden? → ggf. Spec-Zusammenfassungen statt Volltexte
    Ja zusammenfassungen sind besser.
- [ ] Soll `--deep` (RequirementsPairwise) in einem späteren SPEC spezifiziert werden?

## 10. Änderungshistorie

| Datum      | Version | Autor | Änderung            |
| ---------- | ------- | ----- | ------------------- |
| 2026-05-30 | 0.1.0   | Boris | Initiale Erstellung |
