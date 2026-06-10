---
id: CON-0168
project: PRJ-0001
title: "Skill-Scope-Einträge und eindeutige `/sdd`-Übersicht"
type: behavior
format: markdown
spec: SPEC-0044
version: 0.1.0
status: approved
artifact: "contracts/behavior/skill-scope-eintraege.md"
tests:
  - TST-0196
---

# Contract: Skill-Scope-Einträge und eindeutige `/sdd`-Übersicht

> **Spec:** SPEC-0044 · **Typ:** Verhalten · **Status:** draft

## Zweck

Garantiert, dass jeder Skill einen `scope:`-Eintrag im Frontmatter hat, der seinen
exklusiven Zuständigkeitsbereich in einem Satz beschreibt, und dass die `/sdd`-Übersicht
pro Aufgabe genau einen Skill anzeigt (keine Duplikate).

## Garantien

- Jede Skill-Markdown-Datei im Projektverzeichnis (`.claude/commands/sdd-*.md` oder
  analog) enthält im YAML-Frontmatter einen `scope:`-Schlüssel mit einem Satz
- Kein zwei Skill-Einträge in der `/sdd`-Übersicht decken denselben Aufgabenbereich ab
- Die `/sdd`-Übersicht listet jeden Skill mit seinem `scope:`-Wert neben dem Namen auf
- Überschneidungen zwischen Skills werden im `scope:`-Text aufgelöst, sodass die
  Abgrenzung für einen LLM-Agenten eindeutig ist

## Invarianten

- `grep -L "^scope:" .claude/commands/sdd-*.md` liefert leere Ausgabe (kein Skill fehlt)
- Keine zwei `scope:`-Werte beschreiben dieselbe Aufgabe semantisch
- `/sdd` (Skill-Aufruf) zeigt eine tabellarische Übersicht ohne Duplikate

## Gherkin

```gherkin
Feature: Skill-Scope-Einträge nach Cleanup

  Scenario: Alle Skills haben scope-Eintrag
    Given die Skill-Dateien in .claude/commands/
    When ich alle sdd-*.md Dateien prüfe
    Then hat jede Datei einen "scope:"-Schlüssel im Frontmatter

  Scenario: /sdd Übersicht zeigt jeden Skill einmalig
    When ich /sdd aufrufe
    Then enthält die Ausgabe keine zwei Zeilen mit identischer Aufgabe
    And jede Zeile zeigt "Skill-Name | scope-Beschreibung"

  Scenario: LLM-Agent kann Skill eindeutig auswählen
    Given ein LLM-Agent sucht den Skill für "Contract inhaltlich reviewen"
    When er die scope-Einträge vergleicht
    Then findet er genau einen passenden Skill (sdd-review)
    And keinen zweiten Skill mit überlappender Beschreibung
```
