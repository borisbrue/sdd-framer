---
id: SPEC-0044
title: SDD Cleanup – CLI & Skill Consolidation
type: refactoring
status: draft
owner: Boris
created: 2026-06-09
updated: '2026-06-09'
version: 0.1.0
priority: high
tags:
  - cli
  - skills
  - ux
  - refactoring
depends_on: []
contracts: []
tests: []
fr_test_map: {}
adrs: []
---
# SDD Cleanup – CLI & Skill Consolidation

> **Status:** draft · **Owner:** Boris · **Version:** 0.1.0

## 1. Kontext & Motivation

Das SDD-Tool ist organisch auf über 50 CLI-Befehle in 12 Gruppen und 10 Skills gewachsen.
Dabei sind drei Probleme entstanden:

1. **Unfertige Subsysteme** (`pattern`, `obsidian`, `pwa`, `dev`-Container) belegen Oberfläche
   ohne vollständig nutzbar zu sein.
2. **Doppelungen** (`sdd review-contract` / `/sdd-review`, `sdd generate-holdouts` /
   `/sdd-holdout`, `sdd check-conflicts` / `sdd conflict`) verursachen Verwirrung darüber,
   welcher Weg der kanonische ist.
3. **Inkonsistentes Benennungsschema** erschwert Discoverability für Entwickler und – kritisch –
   für LLM-Agenten, die die Skills programmatisch verwenden: Unklare Grenzen führen zu
   falschen Tool-Auswahlen und redundanten Aufrufen.

Ziel ist eine schlanke, konsistente Oberfläche, auf der jeder Befehl und jeder Skill
eine eindeutige, nicht-überlappende Verantwortung hat.

## 2. Zielsetzung

**Primärziel:**
CLI und Skills so konsolidieren, dass alle Funktionen erhalten bleiben, aber jede Funktion
nur noch an einem kanonischen Ort angeboten wird.

**Erfolgskriterien (messbar):**
- [ ] Jeder Skill hat einen eindeutigen, nicht-überlappenden Zweck (kein Skill deckt
      dasselbe ab wie ein anderer)
- [ ] Die CLI folgt einem konsistenten Benennungsmuster (Verb-Gruppe-Unterbefehl-Schema)
- [ ] Alle Funktionen aus dem heutigen Inventar sind weiterhin nutzbar (kein Feature-Verlust)
- [ ] Kein LLM-Agent muss zwischen zwei Befehlen wählen, die dieselbe Funktion erfüllen

**Nicht-Ziele (explizit):**
- Web-UI-Routen / API-Endpunkte aufräumen (separates Vorhaben)
- Neue Features hinzufügen
- Hub-System komplett entfernen (nur CLI-Cleanup)
- Breaking Changes ohne Migrationshinweis

## 3. User Stories

| ID    | Als …             | möchte ich …                                                    | um …                                                        |
|-------|-------------------|-----------------------------------------------------------------|-------------------------------------------------------------|
| US-01 | Entwickler (neu)  | mit `sdd --help` sofort alle relevanten Befehle verstehen       | ohne Dokumentation loszulegen                               |
| US-02 | LLM-Agent         | pro Aufgabe genau einen Skill/Befehl finden                     | keine Ambiguität bei Tool-Auswahl zu haben                  |
| US-03 | Entwickler (alt)  | wissen, wohin veraltete Befehle verschoben/entfernt wurden      | meine Workflows anpassen zu können                          |
| US-04 | Maintainer        | weniger Stubs und tote Code-Pfade pflegen                       | den Wartungsaufwand zu reduzieren                           |

## 4. Funktionale Anforderungen

- **FR-01:** Die CLI-Gruppen `pattern` und `dev` werden entfernt. `obsidian` und `pwa`
  bleiben erhalten — Obsidian als aktiv genutzter Vault-Sync, PWA als eigenständige
  mobile UI für den Projektserver. Eine Migrationsnotiz für die entfernten Gruppen wird
  in `CHANGELOG.md` ergänzt.

- **FR-02:** CLI-Befehle, die inhaltlich denselben Bereich wie Skills abdecken, bleiben
  erhalten. Skills sind Claude-Code-Shortcuts; die CLI ist die kanonische,
  LLM-agnostische Schnittstelle für alle anderen Agenten. Statt Entfernung werden
  betroffene Befehle in zwei kanonische Verb-Gruppen überführt:

  **`sdd new` – einziger Einstiegspunkt für Erstellung:**
  - `sdd new spec|contract|test|holdout|hotfix` bleibt als **kanonische Erstellungs-Gruppe**
    erhalten und wird um `hotfix` erweitert. Kein `sdd spec new`, kein `sdd contract new`.

  **`sdd review` – einziger Einstiegspunkt für Reviews (neue Gruppe):**
  - `sdd spec review SPEC-ID` → **`sdd review spec SPEC-ID`**
    (SOLID-Analyse + Pattern-Vorschläge; Gegenstück zu `/sdd-review`)
  - `sdd review-contract CON-ID` → **`sdd review contract CON-ID`**
    (LLM-Review Vollständigkeit; Gegenstück zu `/sdd-review`)
  - **`sdd review contract --spec SPEC-ID`** _(neu)_
    Alle Contracts eines Specs sequenziell im Loop reviewen
  - `sdd review-pending` → **`sdd review pending [--auto]`**
    (Contracts im Status `review` auflisten; `--auto` reviewed alle)

  **Weitere Umbenennungen (`sdd <noun> <verb>`):**
  - `sdd generate-holdouts SPEC-ID` → **`sdd holdout generate SPEC-ID`**
  - `sdd test-run SPEC-ID` → **`sdd test run SPEC-ID`**
  - `sdd test-results SPEC-ID` → **`sdd test results SPEC-ID`**
  - `sdd evaluate` → **`sdd holdout run`**

  **Namenskollision auflösen:** Der bisherige `sdd contract review` (Konfliktanalyse
  zwischen Contracts) wird zu **`sdd contract analyze`** umbenannt — `sdd contract`
  enthält damit nur Pipeline-Befehle (propose, analyze, pending), während
  `sdd review contract` das LLM-Review eines einzelnen Contracts ist.

- **FR-03:** Verbleibende Top-Level-Befehle werden in passende Gruppen überführt:
  - `sdd solid-check ARTIFACT-ID` → **`sdd spec solid ARTIFACT-ID`**
    (SOLID-Analyse; bleibt eigenständig aufrufbar für nicht-Claude-LLMs)
  - `sdd regression-check SPEC-ID` → **`sdd spec regression SPEC-ID`**
  - `sdd mark-false-positive PR-NR` → **`sdd autonomy false-positive PR-NR`**
  - `sdd status-check` → intern; wird nur noch vom pre-commit-Hook und `sdd spec start`
    aufgerufen, nicht mehr als öffentlicher Befehl exponiert
  - `sdd level PROJECT-ID` + `sdd set-level PROJECT-ID LEVEL` →
    **`sdd autonomy level PROJECT-ID`** + **`sdd autonomy set-level PROJECT-ID LEVEL`**

- **FR-04:** Jeder Skill erhält im Frontmatter einen `scope:`-Eintrag (1 Satz), der seinen
  exklusiven Zuständigkeitsbereich beschreibt. Überschneidungen werden dabei aufgelöst.

- **FR-05:** Die Skill-Übersicht in `/sdd` zeigt nach dem Cleanup für jede Aufgabe
  genau einen Skill an (keine Duplikate in der Ausgabe).

- **FR-07:** `sdd review contract CON-ID` überarbeitet ausschließlich den Inhalt des
  Contracts (Vollständigkeit, SOLID-Konformität, Klarheit) und setzt den Status auf
  `approved`. Die bisherige Nebenwirkung — automatisches Anlegen einer TST-Datei —
  wird entfernt. Test-Stubs werden ausschließlich über `sdd test generate SPEC-ID CON-ID…`
  erstellt, das den Spec-Kontext via SPEC-ID lädt. Damit sind die beiden Verantwortlichkeiten
  klar getrennt und doppelte Stubs unmöglich.
  `sdd review contract --spec SPEC-ID` iteriert über alle Contracts des Specs und
  ruft für jeden `sdd review contract CON-ID` auf.

- **FR-06:** `sdd init` integriert zwei bisher separate Scaffolding-Befehle direkt
  in den Initialisierungsprozess:

  **Skill-Dateien (agents-md):**
  Prüft, ob die Skill-Dateien des gewählten Providers (z.B. `.claude/commands/sdd-new.md`)
  vorhanden sind. Fehlen sie, werden sie automatisch angelegt — analog zur bestehenden
  `REQUIRED_DIRS`-Logik in `init.py`.

  **GitHub-Actions-Workflow:**
  Fragt interaktiv, ob der CI-Workflow `.github/workflows/sdd-orchestrate.yml` angelegt
  werden soll. Der Workflow triggert `sdd orchestrate` automatisch bei jedem Push auf
  `main`, wenn Spec-Dateien geändert wurden (Dark-Factory-Pfad auf CI). Da dieser Workflow
  einen `ANTHROPIC_API_KEY` als GitHub-Secret benötigt und nicht für alle Projekte
  sinnvoll ist, erfolgt die Anlage nur nach expliziter Bestätigung durch den User.

  Beide bisherigen Befehle entfallen als eigenständige User-Befehle:
  - `sdd new agents-md` → in `sdd init` + `sdd upgrade` (Nachrüsten) integriert
  - `sdd new github-workflow` → in `sdd init` integriert (mit Rückfrage)

## 5. Architektur & Design Patterns

### Facade Pattern
**Begründung:** Jeder Skill ist eine Facade über eine klar abgegrenzte Teilmenge der CLI.
Skills und CLI-Befehle überlappen bewusst: der Skill ist der Claude-Code-Shortcut,
der CLI-Befehl ist die LLM-agnostische Schnittstelle. Nach dem Cleanup hat jede Facade
einen eindeutigen Namen im `<noun> <verb>` Schema.
[Refactoring Guru – Facade](https://refactoring.guru/design-patterns/facade)

### Command Pattern
**Begründung:** Die CLI folgt bereits dem Command-Muster (jeder Befehl kapselt eine
Operation). Das Cleanup sorgt dafür, dass jede Operation genau einem Command-Objekt
entspricht — keine zwei Commands für dieselbe Operation.
[Refactoring Guru – Command](https://refactoring.guru/design-patterns/command)

## 6. Inventar der Änderungen

### Zu entfernende CLI-Gruppen
| Gruppe | Befehle | Grund |
|--------|---------|-------|
| `sdd pattern` | `pattern-suggest`, `pattern accept`, `pattern reject`, `pattern list` | Pattern-Entscheidungen leben in der Spec unter "Architektur & Design Patterns"; separates Register ist redundant |
| `sdd dev` | `start`, `exec`, `close`, `pr`, `build`, `push`, `up`, `down` | Container-Lifecycle wird intern von `sdd spec start`/`finalize` und `sdd orchestrate` verwaltet; `DevContainerManager`-Modul bleibt als interne Dependency erhalten |

### Verbleibende CLI-Gruppen (bisher als Kandidaten genannt, bleiben erhalten)
| Gruppe | Grund |
|--------|-------|
| `sdd obsidian` | Aktiv genutzter bi-direktionaler Vault-Sync mit Obsidian |
| `sdd pwa` | Eigenständige mobile UI für den SDD-Projektserver (kein Overlap mit `sdd ui`) |

### Zu entfernende interne Stubs
| Befehl | Grund |
|--------|-------|
| `sdd implement` | wirft `NotImplementedError`; Funktion liegt ausschließlich im Skill `/sdd-implement` |
| `sdd status-check` (public) | wird intern von pre-commit-Hook und `sdd spec start` aufgerufen; kein direkter User/LLM-Use-Case |
| `sdd new agents-md` | Funktion wird in `sdd init` (Erstanlage) und `sdd upgrade` (Nachrüsten) integriert (FR-06) |
| `sdd new github-workflow` | Funktion wird in `sdd init` integriert (interaktive Rückfrage; FR-06) |

### Umbenennungen nach `sdd <noun> <verb>` Schema
CLI-Befehle mit Skill-Gegenstück bleiben erhalten (LLM-Agnostik), werden aber in das
einheitliche Benennungsschema überführt. `Alt → Neu`:

| Alt | Neu | Skill-Gegenstück |
|-----|-----|-----------------|
| `sdd review-contract CON-ID` | `sdd review contract CON-ID` | `/sdd-review` |
| `sdd spec review SPEC-ID` | `sdd review spec SPEC-ID` | `/sdd-review` |
| `sdd review-pending` | `sdd review pending [--auto]` | — |
| `sdd generate-holdouts SPEC-ID` | `sdd holdout generate SPEC-ID` | `/sdd-holdout` |
| `sdd evaluate` | `sdd holdout run` | — |
| `sdd test-run SPEC-ID` | `sdd test run SPEC-ID` | — |
| `sdd test-results SPEC-ID` | `sdd test results SPEC-ID` | — |
| `sdd solid-check ARTIFACT-ID` | `sdd spec solid ARTIFACT-ID` | — |
| `sdd regression-check SPEC-ID` | `sdd spec regression SPEC-ID` | — |
| `sdd mark-false-positive PR` | `sdd autonomy false-positive PR` | — |
| `sdd level PROJECT-ID` | `sdd autonomy level PROJECT-ID` | — |
| `sdd set-level PROJECT-ID LVL` | `sdd autonomy set-level PROJECT-ID LVL` | — |
| `sdd new spec\|contract\|test\|holdout` | `sdd new spec\|contract\|test\|holdout\|hotfix` (+hotfix neu) | — |

### Namenskollision auflösen
| Aktuell | Neu | Grund |
|---------|-----|-------|
| `sdd contract review SPEC-ID CON-ID…` | `sdd contract analyze SPEC-ID CON-ID…` | gibt `sdd review contract` eindeutig für LLM-Review frei; `sdd contract` enthält nur Pipeline-Befehle |

### Verbleibende kanonische Top-Level-Befehle (kein Gruppenfit)
| Befehl | Begründung |
|--------|------------|
| `sdd init` | Einmalige Projekt-Initialisierung; kein sinnvoller Noun |
| `sdd upgrade` | Paket-Migration; kein sinnvoller Noun |
| `sdd validate` | Querschnittsbefehl über alle Artefakttypen |
| `sdd trace` | Erzeugt projektweite Matrix |
| `sdd orchestrate` | Autonomer Dark-Factory-Pfad |
| `sdd maintenance` | CI/Drift-Sweep |
| `sdd install-hooks` | Git-Setup; Einmalaufruf |

## 7. Contracts (was wird garantiert)

*(werden nach Spec-Approval ergänzt)*

## 8. Tests (wie wird verifiziert)

*(werden nach Contract-Approval ergänzt)*

## 9. Offene Fragen

- [x] ~~Werden CLI-Befehle mit Skill-Gegenstück entfernt?~~ → Nein. CLI = LLM-agnostische
      Schnittstelle, Skills = Claude-Code-Shortcut. Beide Ebenen bleiben, CLI wird umbenannt.
- [ ] Sollen `sdd hub`-Befehle ebenfalls entfernt oder nur dokumentiert werden, dass sie
      ein eigenständiges Subsystem sind?
- [ ] Braucht `/sdd-review` einen klareren Namen, um seinen Scope (SOLID + Patterns +
      LLM-Vollständigkeit) von `/sdd-validate` (Frontmatter + Links) abzugrenzen?
- [ ] Werden für umbenannte Befehle Deprecation-Aliases in einer Übergangsversion benötigt
      (alter Name gibt Hinweis auf neuen Namen), oder ist Hard-Cut ausreichend?

## 10. Implementierungsreihenfolge

1. Inventar finalisieren (abgeschlossen mit dieser Spec)
2. CLI: Gruppen `pattern` und `dev` entfernen
3. CLI: Neue Verb-Gruppen `sdd new` (+ hotfix) und `sdd review` (spec, contract, pending) anlegen; alte Befehle umziehen
4. CLI: `sdd review contract --spec SPEC-ID` Loop-Variante implementieren (FR-02)
5. CLI: Top-Level-Befehle einordnen (`sdd spec solid`, `sdd spec regression`, `sdd autonomy …`)
6. CLI: `sdd init` — Skill-Dateien-Check + GitHub-Actions-Rückfrage integrieren (FR-06); `sdd upgrade` — Nachrüst-Logik ergänzen
7. `lifecycle.py`: TST-Anlage aus `review_contract()` entfernen (FR-07)
8. Skills: `scope:`-Eintrag in alle Skill-Frontmatter ergänzen (FR-04)
9. Skills: `/sdd` Übersicht aktualisieren (FR-05)
10. `CHANGELOG.md` mit Migrationshinweisen ergänzen
11. Tests & Validierung

## 11. Änderungshistorie

| Datum      | Version | Autor  | Änderung            |
|------------|---------|--------|---------------------|
| 2026-06-09 | 0.1.0   | Boris  | Initiale Erstellung |
