---
id: SPEC-0031
title: Hotfix Flow
type: feature
status: implemented
owner: Boris
created: 2026-05-30
updated: '2026-05-30'
version: 0.1.0
priority: high
tags: []
depends_on: []
contracts:
- CON-0119
- CON-0120
tests:
- TST-0138
- TST-0139
adrs: []
started_at: '2026-05-30T10:10:19Z'
---
# Hotfix Flow

> **Status:** draft · **Owner:** Boris · **Version:** 0.1.0

## 1. Kontext & Motivation

Der bestehende SDD-Flow (Spec → Review → Contracts → Tests → Decompose →
Implement → Finalize) ist für kleine Bugfixes überdimensioniert. Er erzeugt
hohen Token-Verbrauch und Prozessoverhead. Für einfache Korrekturen — ein
falscher Defaultwert, ein kaputtes CLI-Argument, ein fehlender Fallback — ist
ein schlanker Alternativpfad nötig, der direkt zur Implementierung führt.

## 2. Zielsetzung

**Primärziel:**
Ein eigenständiger Hotfix-Flow, der einen Fehler identifiziert, eine
Implementierung vornimmt und das Ergebnis einspielt — mit minimalem
Token-Verbrauch und ohne den vollen SDD-Overhead.

**Erfolgskriterien (messbar):**

- [ ] `sdd hotfix start "beschreibung"` erzeugt einen Hotfix-Eintrag in
      weniger als 3 Sekunden (keine LLM-Calls beim Start)
- [ ] Der komplette Hotfix-Zyklus (start → implement → finalize) benötigt
      weniger als 5 CLI-Aufrufe
- [ ] Das `/sdd-hotfix`-Skill führt durch den gesamten Flow ohne Rückfragen
      zu SOLID, Contracts oder Tests
- [ ] Hotfix-Einträge erscheinen im Audit-Log (`sdd status`)

**Nicht-Ziele (explizit):**

- Kein SOLID-Check
- Keine Contracts
- Keine Tests (weder Stubs noch Ausführung)
- Keine Holdout-Evaluation
- Kein Decompose / Distribute / Orchestrate
- Kein Dev-Container-Start

**Gate-Ausnahmen:**

Der Hotfix-Flow ist bewusst vom Execution-Gate (SPEC-0014) ausgenommen —
Contracts und Tests sind für Hotfixes keine Voraussetzung. Ebenso ist der
SOLID-Check-Pflichtschritt (SPEC-0015) für Hotfix-Commits ausgenommen.
Diese Ausnahmen gelten ausschließlich für Änderungen die über
`sdd hotfix finalize` eingespielt werden.

## 3. Architektur & Design Patterns

### Pattern 1 — Command
**Zweck:** Die drei Hotfix-Aktionen (`start`, `finalize`, `abort`) sind
eigenständige Commands, die den Hotfix-Lebenszyklus kapseln. Jeder Command
ändert den Status des Hotfix-Records atomar.

**Refactoring Guru:** https://refactoring.guru/design-patterns/command

```
HotfixCommand (ABC)
  ├── StartCommand     → Status: open
  ├── FinalizeCommand  → Status: done  + Audit-Log-Eintrag
  └── AbortCommand     → Status: aborted
```

### Pattern 2 — Template Method
**Zweck:** Der `/sdd-hotfix`-Skill definiert ein festes Skelett
(Identifizierung → Implementierung → Finalisierung), während jeder Schritt
angepasst werden kann (z.B. ob ein Regression-Check mitläuft oder nicht).

**Refactoring Guru:** https://refactoring.guru/design-patterns/template-method

```
HotfixFlow (Skelett)
  ├── identify()     → Bug beschreiben + HF-Record anlegen
  ├── implement()    → Code-Änderung direkt vornehmen
  └── finalize()     → Commit + Audit-Log
```

## 4. Funktionale Anforderungen

- **FR-01:** `sdd hotfix start "<beschreibung>"` legt einen minimalen
  Hotfix-Record in `.sdd/hotfixes/HF-XXXX.md` an. Kein LLM-Aufruf,
  kein Container-Start.
- **FR-02:** Der Hotfix-Record enthält: `id` (HF-XXXX), `description`,
  `status` (open / done / aborted), `created`, `commit` (leer bis finalize).
- **FR-03:** `sdd hotfix finalize HF-XXXX` committet alle staged Changes,
  trägt den Commit-Hash in den Record ein und setzt `status: done`.
- **FR-04:** `sdd hotfix abort HF-XXXX` setzt `status: aborted` ohne Commit.
- **FR-05:** `sdd hotfix list` zeigt alle offenen Hotfixes tabellarisch.
- **FR-06:** Abgeschlossene Hotfixes erscheinen in `sdd status` unter einem
  eigenen Abschnitt (ohne den Spec-basierten Flow zu beeinflussen).
- **FR-07:** `/sdd-hotfix`-Skill führt durch den Flow interaktiv:
  Bug beschreiben → Code-Änderung implementieren → `sdd hotfix finalize`.

## 5. User Stories

| ID    | Als ...    | möchte ich ...                                         | um ...                                              |
| ----- | ---------- | ------------------------------------------------------ | --------------------------------------------------- |
| US-01 | Entwickler | einen Bugfix in < 5 Minuten einspielen                 | den Fehler schnell zu beheben ohne Spec-Overhead    |
| US-02 | Entwickler | den Hotfix mit einem einzigen Commit abschließen       | die Git-History sauber zu halten                   |
| US-03 | CI-Pipeline| `sdd hotfix finalize` skriptfähig aufrufen             | Hotfixes automatisiert einzuspielen                 |
| US-04 | Entwickler | alle offenen Hotfixes auf einen Blick sehen            | nichts zu vergessen                                 |

## 6. Contracts

*(werden in `/sdd-new contract` ergänzt)*

## 7. Tests

*(werden in `/sdd-new test` ergänzt)*

## 8. Implementierungsreihenfolge

1. `.sdd/hotfixes/`-Verzeichnis + minimales Frontmatter-Schema
2. `sdd hotfix start` — Record anlegen (kein LLM)
3. `sdd hotfix finalize` — Commit + Record aktualisieren
4. `sdd hotfix abort` + `sdd hotfix list`
5. `sdd status` — Hotfix-Abschnitt ergänzen
6. `/sdd-hotfix`-Skill erstellen

## 9. Offene Fragen

- [ ] Soll `sdd hotfix finalize` optional einen LLM-Regression-Check (SPEC-0030
      Stufe 1, regelbasiert) ausführen? Würde Sicherheit erhöhen ohne großen
      Token-Overhead.
- [ ] HF-IDs global (HF-0001) oder pro Tag (HF-20260530-01)?

## 10. Änderungshistorie

| Datum      | Version | Autor | Änderung            |
| ---------- | ------- | ----- | ------------------- |
| 2026-05-30 | 0.1.0   | Boris | Initiale Erstellung |
