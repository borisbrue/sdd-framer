---
id: TST-0196
project: PRJ-0001
title: "Skill-Scope-Einträge im Frontmatter aller Skills"
level: unit
spec: SPEC-0044
contract: CON-0168
status: draft
framework: pytest
artifact: "tests/unit/test_tst_0196.py"
tags:
  - skills
  - cleanup
---

# Test: Skill-Scope-Einträge

> **Level:** unit · **Spec:** SPEC-0044 · **Contract:** CON-0168

## Was wird geprüft?

Prüft dass alle `sdd-*.md` Skill-Dateien in `.claude/commands/` einen
`scope:`-Eintrag im YAML-Frontmatter haben und kein Eintrag leer ist.

## Vorbedingungen

- `.claude/commands/sdd-*.md` Dateien existieren nach Implementierung von SPEC-0044

## Ablauf

1. Alle `sdd-*.md` in `.claude/commands/` einlesen
2. Jede Datei: Prüfe `scope:` im Frontmatter vorhanden
3. Jede Datei: Prüfe `scope:`-Wert nicht leer

## Verknüpfung mit Contract

- [x] Jede Skill-Datei hat `scope:`-Schlüssel
- [x] Kein `scope:`-Wert ist leer
