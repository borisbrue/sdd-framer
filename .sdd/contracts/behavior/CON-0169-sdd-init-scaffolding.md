---
id: CON-0169
project: PRJ-0001
title: "`sdd init` integriert Skill-Dateien-Check und GitHub-Actions-Rückfrage"
type: behavior
format: markdown
spec: SPEC-0044
version: 0.2.0
status: approved
artifact: "contracts/behavior/sdd-init-scaffolding.md"
tests:
  - TST-0201
---

# Contract: `sdd init` Scaffolding-Integration

> **Spec:** SPEC-0044 · **Typ:** Verhalten · **Status:** draft

## Zweck

Garantiert, dass `sdd init` automatisch Skill-Dateien anlegt wenn sie fehlen, und
interaktiv fragt ob der GitHub-Actions-Workflow erstellt werden soll. Die bisherigen
eigenständigen Befehle `sdd new agents-md` und `sdd new github-workflow` entfallen.

## Garantien

### Skill-Dateien (agents-md)
- `sdd init` prüft ob die Skill-Dateien des gewählten Providers vorhanden sind
- Fehlen sie, werden sie automatisch angelegt (analog zur `REQUIRED_DIRS`-Logik)
- Kein manueller Aufruf von `sdd new agents-md` nötig
- `sdd upgrade` enthält die Nachrüst-Logik für bestehende Projekte
- `sdd upgrade` ersetzt eine vorhandene Skill-Datei, wenn ihre Kopfzeile
  `sdd-blueprint: true` trägt und die Version älter ist als die des Blueprints.
  Ein vorangestelltes Frontmatter (`scope:`) bleibt erhalten. Dateien ohne diese
  Kopfzeile gelten als eigene und werden nie angefasst.

> **v0.2.0 (2026-09-11, #134):** Die Nachrüstung kam mit #129. Vorher stand sie
> nur in der Hilfe. Das Ersetzen älterer Blueprint-Fassungen ist neu: Ein Projekt
> behielt sonst auf Dauer Skills, die auf entfernte Befehle zeigten und die
> Gate-Kette nicht kannten; nur `sdd init --force-skills` half, und das
> überschrieb auch eigene Dateien.

### GitHub-Actions-Workflow
- `sdd init` fragt interaktiv: "GitHub-Actions-Workflow anlegen? (ja/nein)"
- Bei "ja": `.github/workflows/sdd-orchestrate.yml` wird angelegt
- Der Workflow triggert `sdd pipeline run <SPEC> --auto` bei Push auf `main` wenn Spec-Dateien geändert wurden (seit SPEC-0062, vorher `sdd orchestrate`)
- Die Frage wird immer gestellt (CI braucht ein Rollen-Profil ohne lokales `claude`; `ANTHROPIC_API_KEY` nur bei `provider: anthropic`)
- Bei "nein": Workflow-Datei wird nicht angelegt; kein Fehler

### Entfernte Befehle
- `sdd new agents-md` ist nicht mehr als eigenständiger User-Befehl verfügbar
- `sdd new github-workflow` ist nicht mehr als eigenständiger User-Befehl verfügbar

## Invarianten

- `sdd init` läuft ohne Fehler durch auch wenn Skill-Dateien schon vorhanden sind
  (idempotent)
- GitHub-Actions-Frage erscheint genau einmal pro `sdd init`-Aufruf
- Ohne GitHub-Actions-Bestätigung wird keine Workflow-Datei angelegt
- `sdd upgrade` rüstet Skill-Dateien nach ohne nochmals nach GitHub-Actions zu fragen

## Gherkin

```gherkin
Feature: sdd init Scaffolding-Integration

  Scenario: sdd init legt fehlende Skill-Dateien automatisch an
    Given ein Projekt ohne .claude/commands/sdd-new.md
    When ich `sdd init` aufrufe
    Then wird .claude/commands/sdd-new.md automatisch angelegt
    And alle weiteren fehlenden Skill-Dateien werden angelegt

  Scenario: sdd init fragt nach GitHub-Actions-Workflow
    When ich `sdd init` aufrufe
    Then erscheint die Frage "GitHub-Actions-Workflow anlegen?"
    And bei Antwort "ja" wird .github/workflows/sdd-orchestrate.yml erstellt
    And bei Antwort "nein" wird keine Workflow-Datei erstellt

  Scenario: sdd new agents-md ist nicht mehr öffentlich
    When ich `sdd new agents-md` aufrufe
    Then endet der Prozess mit Exit-Code ungleich 0
    And die Ausgabe enthält Hinweis auf "sdd init"

  Scenario: sdd upgrade rüstet Skill-Dateien nach
    Given ein bestehendes Projekt mit veralteten Skill-Dateien
    When ich `sdd upgrade` aufrufe
    Then werden fehlende Skill-Dateien nachgerüstet
    And es erscheint keine GitHub-Actions-Frage

  Scenario: sdd upgrade ersetzt eine ältere Blueprint-Fassung
    Given .claude/commands/sdd-review.md trägt "version: 0.4.0 | sdd-blueprint: true"
    And das Blueprint liefert sdd-review.md in Version 0.6.0
    When ich `sdd upgrade` aufrufe
    Then enthält .claude/commands/sdd-review.md die Fassung 0.6.0
    And ein vorangestelltes Frontmatter bleibt erhalten

  Scenario: sdd upgrade lässt eigene Skill-Dateien in Ruhe
    Given .claude/commands/sdd-review.md ohne die Kopfzeile "sdd-blueprint: true"
    When ich `sdd upgrade` aufrufe
    Then bleibt die Datei byte-gleich
```
