---
id: TST-0211
project: PRJ-0001
title: "Pattern-Katalog-Kontext – Prompt-Aufbau und Skill-Kontextladen"
level: unit
spec: SPEC-0048
contract: CON-0182
status: draft
framework: pytest
artifact: "tests/unit/test_tst_0211.py"
tags:
  - patterns
  - design-decisions
  - llm-integration
---

# Test: Pattern-Katalog-Kontext – Prompt-Aufbau und Skill-Kontextladen

> **Level:** unit · **Spec:** SPEC-0048 · **Contract:** CON-0182

## Was wird geprüft?

Prüft, dass `_build_pattern_prompt()` den Katalog-Kontext-Abschnitt korrekt
ein-/ausblendet, dass `PatternSuggester.suggest()` `catalog_summary()` mit dem
eigenen `exclude_spec_id` aufruft und das Ergebnis durchreicht, und dass die
Skill-Datei `.claude/commands/sdd-implement.md` den neuen Kontextladeschritt
für den globalen Katalog enthält (FR-07, nicht über Python-API testbar).

## Vorbedingungen

- `_build_pattern_prompt()` erhält neuen optionalen Parameter `catalog_context`
- `PatternSuggester.suggest()` ruft `PatternRegistry.catalog_summary()` auf

## Ablauf

1. `_build_pattern_prompt(..., catalog_context="")` → kein Abschnitt
   "BEREITS AKZEPTIERTE PATTERNS IM PROJEKT" im Prompt
2. `_build_pattern_prompt(..., catalog_context="- Observer (...): ...")` → Abschnitt
   vorhanden, Inhalt enthalten
3. Prompt-Reihenfolge bleibt invariant (Instruktion vor Katalog-Kontext vor Output-Format)
4. `PatternSuggester.suggest()` mit gemocktem `PatternRegistry` → `catalog_summary`
   wird mit `exclude_spec_id=<eigene ID>` aufgerufen
5. `.claude/commands/sdd-implement.md` enthält die Zeichenkette
   "Etablierte Patterns im Projekt" und einen Verweis auf `_catalog.json`

## Verknüpfung mit Contract (CON-0182)

- [x] INV-01: leerer Katalog-Kontext → kein Abschnitt im Prompt
- [x] INV-02: nicht-leerer Katalog-Kontext → Abschnitt vorhanden
- [x] INV-03: eigene Spec/Contract-ID wird ausgeschlossen (via `exclude_spec_id`)
- [x] INV-04: Prompt-Reihenfolge invariant
- [x] Szenario: /sdd-implement zeigt Katalog-Zusammenfassung im Kontextschritt (Doku-Check)
