---
id: CON-0067
title: "pr-document-schema"
type: data
format: json-schema
spec: SPEC-0021
version: 0.2.0
status: draft
artifact: "contracts/data/pr-document.schema.json"
tests: [TST-0076]
---

# Contract: pr-document-schema

> **Spec:** SPEC-0021 · **Typ:** Daten (JSON Schema) · **Status:** draft

## Zweck

Definiert die Pflichtfelder des PR-Dokuments (`.sdd/prs/PR-SPEC-XXXX.md`),
das `sdd dev pr` nach erfolgreichem Gate erstellt.

**Abhängigkeiten:**
- `test_result` und `tests_passed`/`tests_total` übernehmen das Format aus
  **CON-0017** (Test Run Results API) — kein eigenständiges Format.
- `spec_id`-Format folgt **CON-0025** (Execution Gate Phase State Machine).
- Das Verzeichnis `.sdd/prs/` wird analog zu `.sdd/pipeline/` (CON-0009/CON-0030)
  als SDD-internes Artefakt-Verzeichnis behandelt.

## Garantien

- **G-01:** Jedes PR-Dokument enthält: `spec_id`, `branch`, `created`,
  `test_result`, `merge_command` als Pflichtfelder.
- **G-02:** Das Dokument ist valides Markdown mit YAML-Frontmatter.
- **G-03:** `merge_command` enthält den konkreten, ausführbaren Git-Befehl
  mit dem Branch aus dem `branch`-Feld.

## Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "SDD Dev PR-Dokument Frontmatter",
  "type": "object",
  "required": ["spec_id", "branch", "created", "test_result", "merge_command"],
  "properties": {
    "spec_id": {
      "type": "string",
      "pattern": "^SPEC-[0-9]{4}$",
      "description": "SPEC-ID — Format gemäß CON-0025"
    },
    "branch": {
      "type": "string",
      "pattern": "^dev/SPEC-[0-9]{4}$",
      "description": "Git-Branch-Name für interaktive Entwicklung (dev/-Präfix)"
    },
    "created": {
      "type": "string",
      "format": "date",
      "description": "Erstellungsdatum im Format YYYY-MM-DD"
    },
    "test_result": {
      "type": "string",
      "enum": ["passed", "failed", "skipped"],
      "description": "Ergebnis des letzten Test-Laufs — Werte gemäß CON-0017"
    },
    "tests_passed": {
      "type": "integer",
      "minimum": 0,
      "description": "Anzahl der bestandenen Tests (aus CON-0017 Test Run Result)"
    },
    "tests_total": {
      "type": "integer",
      "minimum": 0,
      "description": "Gesamtzahl der Tests (aus CON-0017 Test Run Result)"
    },
    "merge_command": {
      "type": "string",
      "description": "Ausführbarer git-Befehl für den Merge",
      "example": "git checkout main && git merge dev/SPEC-0021"
    },
    "diff_stat": {
      "type": "string",
      "description": "Ausgabe von git diff main..dev/SPEC-XXXX --stat"
    },
    "pr_strategy": {
      "type": "string",
      "enum": ["local", "github"],
      "default": "local"
    }
  }
}
```

## Invarianten

- **INV-01:** `spec_id` und `branch` sind konsistent: `SPEC-0021` → `dev/SPEC-0021`.
- **INV-02:** `test_result: passed` nur wenn `tests_passed == tests_total` und
  beide > 0.
- **INV-03:** `merge_command` enthält den Branch-Namen aus dem `branch`-Feld.
- **INV-04:** `.sdd/prs/` wird von `sdd dev pr` automatisch erstellt falls nicht
  vorhanden (analog zu `.sdd/pipeline/`).
