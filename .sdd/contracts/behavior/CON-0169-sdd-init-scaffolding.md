---
id: CON-0169
project: PRJ-0001
title: "`sdd init` integriert Skill-Dateien-Check und GitHub-Actions-Rückfrage"
type: behavior
format: markdown
spec: SPEC-0044
version: 0.1.1
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
```
