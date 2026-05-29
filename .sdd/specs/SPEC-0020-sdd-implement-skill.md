---
id: SPEC-0020
title: "/sdd-implement – Claude Skill für geführte TDD-Implementierung"
status: implemented
owner: Boris
created: 2026-05-16
updated: 2026-05-16
version: 0.1.0
priority: high
tags:
  - claude-code
  - skill
  - tdd
  - dark-factory
  - implementation
  - blueprint
depends_on:
  - SPEC-0019
  - SPEC-0004
contracts:
  - CON-0063
  - CON-0064
tests:
  - TST-0072
  - TST-0073
adrs: []
---

# /sdd-implement – Claude Skill für geführte TDD-Implementierung

> **Status:** implemented · **Owner:** Boris · **Version:** 0.1.0

## 1. Kontext & Motivation

Das Dark Factory Pattern (SPEC-0004) definiert zwei Ausführungspfade:

| Pfad | Trigger | Zielgruppe |
|---|---|---|
| **Autonom** | GitHub Actions → `sdd orchestrate` | Level 4, keine menschliche Beteiligung |
| **Interaktiv** | Claude Code CLI → `/sdd-implement` | Level 2–3, Entwickler im Loop |

Der autonome Pfad (SPEC-0004) ist implementiert. Der interaktive Pfad fehlt:
Entwickler die lokal arbeiten, müssen nach `sdd start SPEC-XXXX` (SPEC-0019) den
Code ohne strukturierten Kontext schreiben. Claude Code hat keinen standardisierten
Zugang zu Spec, Contracts, Holdout-Isolation oder Test-Stubs.

**Das Problem:** Ein Entwickler öffnet Claude Code nach `sdd start` und fragt
"Implementiere das Feature". Claude hat keinen Kontext über:
- Welche Contracts eingehalten werden müssen
- Welche Test-Stubs bereits existieren
- Was die Holdout-Szenarien prüfen (die er explizit NICHT sehen darf)
- Welche SOLID-Regeln für diese Spec gelten (Pattern-Register)

**Die Lösung:** `/sdd-implement SPEC-XXXX` als Claude Code Skill (.claude/commands/sdd-implement.md).
Der Skill lädt strukturiert den kompletten Implementierungskontext, führt Claude durch
TDD-Zyklen und schließt mit Validierung ab – ohne dass der Entwickler die CLI-Details kennt.

---

## 2. Zielsetzung

**Primärziel:**
Entwickler können nach `sdd start SPEC-XXXX` den Befehl `/sdd-implement SPEC-XXXX`
eingeben und erhalten einen vollständig geführten TDD-Zyklus: Kontext laden →
Tests rot → Code schreiben → Tests grün → validieren → Status setzen.

**Erfolgskriterien (messbar):**

- [ ] `/sdd-implement SPEC-XXXX` lädt automatisch: Spec-Inhalt, alle verlinkten Contracts,
      Pattern-Register-Einträge, bestehende Test-Stubs (kein Holdout-Inhalt)
- [ ] Claude schreibt Implementierungscode, führt pytest aus (Bash-Tool) und iteriert
      bis alle Test-Stubs ohne `NotImplementedError` bestehen
- [ ] Holdout-Szenarien (`.sdd/holdout/`) werden explizit von der Kontextladung ausgeschlossen
      (Isolation analog SPEC-0004 Abschnitt 3.1)
- [ ] Nach grünen Tests: Claude ruft `sdd validate` auf und erklärt eventuelle Fehler
- [ ] Skill schlägt am Ende vor: `sdd orchestrate SPEC-XXXX` für vollautomatischen
      Evaluator-Lauf (Holdout-Prüfung durch LLM-2)
- [ ] Skill-Datei ist Teil des `sdd init`-Blueprints (`.sdd/templates/agents-md/commands/`)
- [ ] Skill-Datei < 200 Zeilen (SPEC-0018 NFR)

**Nicht-Ziele:**
- Kein Ersetzen von `sdd orchestrate` – der Skill ist der interaktive Vorlauf
- Kein direktes Ausführen der Holdout-Evaluierung (das macht `sdd evaluate`)
- Kein automatisches `git commit` oder PR-Erstellung
- Kein Ersetzen von SPEC-0018-Skills (`/sdd-new`, `/sdd-validate` etc.)
- Kein Erzwingen von 100 % Test-Coverage (nur die generierten Stubs müssen grün sein)

---

## 3. Architektur & Design

### 3.1 Skill-Datei im Blueprint

```
sdd-framer/
└── .sdd/
    └── templates/
        └── agents-md/
            └── commands/
                └── sdd-implement.md    ← NEU (SPEC-0020)
```

`sdd init` kopiert die Datei nach `.claude/commands/sdd-implement.md` im Ziel-Projekt
(analog SPEC-0018 FR-01/FR-02: Idempotenz, kein Überschreiben ohne `--force-skills`).

### 3.2 Skill-Ablauf (Template Method Pattern)

```
/sdd-implement SPEC-XXXX

  Phase 1: Vorbedingungen prüfen
    └─ .sdd/config.yaml vorhanden? (sonst: "sdd init zuerst")
    └─ SPEC-XXXX hat status: in-progress? (sonst: "sdd start SPEC-XXXX zuerst")
    └─ sdd CLI verfügbar? (which sdd)

  Phase 2: Kontext laden (Allowlist-Prinzip – kein Holdout)
    └─ Spec-Datei vollständig lesen
    └─ Alle verlinkten Contracts lesen (aus Frontmatter: contracts: [...])
    └─ Pattern-Register lesen (.sdd/patterns/SPEC-XXXX-patterns.json) falls vorhanden
    └─ AGENTS.md lesen falls vorhanden
    └─ Test-Stub-Dateien lesen (aus tests/ – NUR Dateien die in TST-Dokumenten als
       artifact referenziert sind oder dem Pattern test_tst_*.py entsprechen)
    └─ .sdd/holdout/ wird NICHT gelesen (explizit ausgeschlossen)

  Phase 3: Implementierungsplan erstellen
    └─ Claude analysiert Spec + Contracts und entwirft Implementierungsstruktur
    └─ Zeigt Plan (Dateien, Klassen, Funktionen) und fragt nach Bestätigung

  Phase 4: TDD-Zyklus
    └─ Schreibe Implementierungscode (eine logische Einheit pro Iteration)
    └─ Führe pytest aus: pytest tests/ -x --tb=short (Bash-Tool)
    └─ Bei Fehler: analysiere Fehlermeldung, korrigiere Code, wiederhole
    └─ Bei grünen Tests: weiter zur nächsten logischen Einheit
    └─ Zyklus endet wenn alle Test-Stubs bestehen

  Phase 5: Validierung & Abschluss
    └─ sdd validate → Fehler erklären und beheben
    └─ Zusammenfassung: N Tests grün, Validierung sauber
    └─ Vorschlag: sdd orchestrate SPEC-XXXX (Holdout-Evaluierung mit LLM-2)
```

### 3.3 Holdout-Isolation (kritisch)

Der Skill liest Dateien ausschließlich nach **Allowlist**:

```
ERLAUBT:
  .sdd/specs/SPEC-XXXX-*.md
  .sdd/contracts/**/*.md  (nur verlinkte CON-IDs)
  .sdd/patterns/SPEC-XXXX-patterns.json
  AGENTS.md
  tests/**/test_*.py      (nur Stubs, kein Holdout)

VERBOTEN (nie lesen, nie erwähnen):
  .sdd/holdout/           ← explizit ausgeschlossen
```

Claude darf die Existenz von Holdout-Szenarien erwähnen, aber deren Inhalt
niemals lesen oder im Implementierungskontext verwenden. Die Isolation erzwingt,
dass der Code gegen Contracts schreibt – nicht gegen bekannte Testfälle.

### 3.4 Design Patterns

#### Template Method Pattern (Behavioral)
**Anwendung:** Die 5 Phasen (Prüfen → Laden → Planen → TDD-Zyklus → Abschluss)
bilden den invarianten Algorithmus. Jede Phase kann je nach Projekt-Kontext
unterschiedlich ausgeprägt sein (z. B. mit/ohne Pattern-Register, mit/ohne AGENTS.md).

**Begründung:** Alle Implement-Läufe folgen demselben Grundablauf (OCP). Neue
Kontextquellen (z. B. Architektur-Diagramme) können als neue Sub-Schritte in
Phase 2 eingefügt werden ohne den Gesamtablauf zu ändern.

#### Facade Pattern (Structural)
**Anwendung:** Der Skill kapselt alle CLI-Aufrufe (`sdd validate`, `sdd orchestrate`,
`pytest`) hinter beschreibenden Instruktionen. Claude führt die Befehle aus,
der Entwickler sieht nur das Ergebnis.

**Alternative:** Direkter Bash-Aufruf ohne Skill-Abstraktion – abgelehnt, weil
ohne Skill kein reproduzierbarer, dokumentierter Workflow existiert.

---

## 4. Skill-Datei-Inhalt (sdd-implement.md)

```markdown
<!-- skill: sdd-implement | version: 0.1.0 | sdd-blueprint: true | updated: 2026-05-16 -->

# /sdd-implement – TDD-Implementierungsphase

## Aufgabe
Implementiere das Feature für die angegebene SPEC vollständig nach TDD:
lade Kontext, schreibe Code, mache Tests grün, validiere.

## Argumente
`$ARGUMENTS` enthält die SPEC-ID (z. B. SPEC-0020).

## Schritt 1: Vorbedingungen
- Prüfe ob `.sdd/config.yaml` existiert. Falls nicht: Meldung "Kein SDD-Projekt.
  Führe zuerst 'sdd init' aus." und abbrechen.
- Prüfe SPEC-Frontmatter: `status` muss `in-progress` sein. Falls nicht:
  Meldung "Führe zuerst 'sdd start $SPEC_ID' aus."
- Prüfe ob `sdd` CLI verfügbar: `which sdd`

## Schritt 2: Kontext laden
Lese folgende Dateien (Allowlist – .sdd/holdout/ wird NICHT gelesen):
1. Die SPEC-Datei: `.sdd/specs/$SPEC_ID-*.md`
2. Alle verlinkten Contracts aus dem `contracts:`-Frontmatter-Feld
3. `.sdd/patterns/$SPEC_ID-patterns.json` falls vorhanden
4. `AGENTS.md` falls vorhanden
5. Test-Stub-Dateien: alle `.py`-Dateien unter `tests/` die `test_tst_` im
   Namen haben oder in TST-Dokumenten als `artifact` referenziert sind

## Schritt 3: Implementierungsplan
Analysiere Spec + Contracts und erstelle einen Implementierungsplan:
- Welche Dateien/Module werden erstellt oder geändert?
- Welche Klassen/Funktionen sind nötig?
- Reihenfolge (Abhängigkeiten zuerst)
Zeige den Plan und frage nach Bestätigung.

## Schritt 4: TDD-Zyklus
Für jede logische Einheit im Plan:
1. Schreibe Implementierungscode
2. Führe Tests aus: `pytest tests/ -x --tb=short`
3. Bei Fehler: analysiere Traceback, korrigiere, wiederhole
4. Iteriere bis alle Tests der aktuellen Einheit grün sind
Fahre fort bis alle Test-Stubs ohne `NotImplementedError` bestehen.

## Schritt 5: Abschluss
1. Führe `sdd validate` aus und erkläre/behebe Fehler
2. Zeige Zusammenfassung: N Tests grün, Validierung OK
3. Schlage vor: `sdd orchestrate $SPEC_ID` für Holdout-Evaluierung (LLM-2)

## Konventionen
- Schreibe keinen Code der Holdout-Szenarien ausnutzt
- Halte dich an die SOLID-Regeln aus dem Pattern-Register
- Schreibe keine neuen Tests – nur die vorhandenen Stubs implementieren
- Kommentare nur wenn das WHY nicht offensichtlich ist
```

---

## 5. Funktionale Anforderungen

**FR-01** Der Skill prüft zu Beginn ob die SPEC `status: in-progress` hat.
Bei anderem Status: klare Fehlermeldung mit nächstem Schritt.

**FR-02** `.sdd/holdout/` wird niemals gelesen. Der Skill enthält einen expliziten
Hinweis an Claude ("NICHT lesen") analog zu SPEC-0004 Abschnitt 3.1.

**FR-03** Der Implementierungsplan wird vor der Ausführung angezeigt und
benötigt eine Bestätigung (kein blindes Starten).

**FR-04** TDD-Zyklus: `pytest tests/ -x --tb=short` nach jeder Code-Einheit.
Bei dauerhaftem Fehler nach 3 Iterationen: Pausieren und Entwickler fragen.

**FR-05** Nach grünen Tests: `sdd validate` ausführen, Fehler erklären und beheben.

**FR-06** Abschluss-Vorschlag immer: `sdd orchestrate SPEC-XXXX` als nächsten Schritt.

**FR-07** Skill-Datei ist Teil des Blueprint-Verzeichnisses (`.sdd/templates/agents-md/commands/sdd-implement.md`).
`sdd init` kopiert sie nach `.claude/commands/sdd-implement.md` (SPEC-0018 FR-01).

**FR-08** Skill-Header gemäß SPEC-0018 FR-04:
`<!-- skill: sdd-implement | version: 0.1.0 | sdd-blueprint: true | updated: 2026-05-16 -->`

---

## 6. Nicht-funktionale Anforderungen

| Attribut | Anforderung |
|---|---|
| Skill-Datei-Größe | < 200 Zeilen (SPEC-0018 NFR) |
| Holdout-Isolation | `.sdd/holdout/` niemals im Skill-Kontext (wie orchestrator.py – Allowlist) |
| Sprache | Skill-Datei auf Deutsch |
| Portabilität | Nur Bash-Befehle (`pytest`, `sdd`, `which`) – keine Shell-spezifischen Features |
| Idempotenz | Mehrfaches `/sdd-implement` auf derselben SPEC ist sicher (Tests wiederholen) |

---

## 7. User Stories

| ID | Als … | möchte ich … | damit … |
|---|---|---|---|
| US-01 | Entwickler | nach `sdd start` `/sdd-implement SPEC-XXXX` eingeben | ich sofort strukturierten Implementierungskontext erhalte |
| US-02 | Entwickler | dass Claude die Tests ausführt und bei Fehlern iteriert | ich nicht manuell pytest aufrufen muss |
| US-03 | Entwickler | sicher sein dass Holdout-Szenarien nicht gelesen werden | die Evaluierung unverzerrt bleibt |
| US-04 | Tech Lead | nach dem Skill `sdd orchestrate` empfohlen bekommen | der Übergang zum vollautonomen Pfad nahtlos ist |
| US-05 | Entwickler | den Implementierungsplan vor Start sehen | ich Korrekturen vor der Ausführung machen kann |

---

## 8. Contracts

| Contract-ID | Typ | Was wird garantiert? |
|---|---|---|
| CON-0063 | behavior | Gherkin: `/sdd-implement` – Vorbedingungen, Holdout-Isolation, TDD-Zyklus-Ablauf |
| CON-0064 | data | Skill-Header-Format + Blueprint-Verzeichnis-Struktur (erweitert CON-0058) |

---

## 9. Tests

| Test-ID | Level | Was prüft der Test? |
|---|---|---|
| TST-0072 | contract | Skill-Datei: Header vorhanden, Holdout-Ausschluss dokumentiert, < 200 Zeilen |
| TST-0073 | acceptance | Gherkin aus CON-0063: `/sdd-implement` auf Sandbox-SPEC → pytest grün, sdd validate sauber |

---

## 10. Implementierungsreihenfolge

```
Phase A: Skill-Datei erstellen
  └─ .sdd/templates/agents-md/commands/sdd-implement.md
     (Inhalt: Abschnitt 4 dieser SPEC)

Phase B: init.py – sdd-implement.md in Blueprint-Kopierliste aufnehmen
  └─ copy_skill_files() kennt bereits das Verzeichnis (SPEC-0018)
  └─ kein zusätzlicher Code nötig – nur Datei im richtigen Verzeichnis ablegen

Phase C: config.yaml-Erweiterung
  └─ skills.commands: sdd-implement-Eintrag ergänzen

Phase D: Contracts + Tests
  └─ CON-0063, CON-0064, TST-0072, TST-0073
```

---

## 11. Verbindung zum Dark Factory Flow

```
Mensch schreibt Spec
  → sdd new contract  →  Contracts (approved)
  → sdd new holdout   →  Holdout-Szenarien (geheim)
  → sdd spec approve  →  Execution Gate
  → sdd start         →  in-progress + Test-Stubs

  ┌─ INTERAKTIV (Level 2–3) ──────────────────────────────────┐
  │  /sdd-implement SPEC-XXXX                                  │
  │    Kontext laden → TDD-Zyklus → Tests grün → validate     │
  │    → Vorschlag: sdd orchestrate                            │
  └───────────────────────────────────────────────────────────┘
        ↓
  sdd orchestrate SPEC-XXXX  (Level 4: vollautonomer Code-LLM)
        ↓
  sdd evaluate  (unabhängiger Evaluator-LLM testet Holdout)
        ↓
  Auto-Merge (sdd:approved) oder Retry
```

---

## 12. Offene Fragen

- [ ] Soll `/sdd-implement` auch `sdd solid-check` aufrufen (SPEC-0015) bevor
      der Code geschrieben wird?
      → Vorschlag: Ja, als Sub-Schritt von Phase 3 (Plan): SOLID-Analyse des Designs
- [ ] Soll der Skill die `AGENTS.md` aktiv anfordern oder nur lesen wenn vorhanden?
      → Lesen wenn vorhanden; fehlende AGENTS.md wird als [WARN] gemeldet

---

## 13. Änderungshistorie

| Datum | Version | Autor | Änderung |
|---|---|---|---|
| 2026-05-16 | 0.1.0 | Boris | Initiale Erstellung |
