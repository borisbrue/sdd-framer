---
id: CON-0067
title: "pr-document-schema"
type: data
format: json-schema
spec: SPEC-0021
version: 0.3.0
status: draft
tests: [TST-0076]
---

# Contract: pr-document-schema

> **Spec:** SPEC-0021 · **Typ:** Daten (JSON Schema) · **Status:** draft

## Zweck

Definiert die Pflichtfelder des PR-Dokuments (`.sdd/prs/PR-SPEC-XXXX.md`).
Es schreibt die lokale PR-Strategie (`LocalGitStrategy`). Die Finalisierung
greift auf sie zurück, wenn `gh pr create` nicht verfügbar ist oder scheitert
(CON-0066, v0.3.0).

> **v0.3.0 (2026-09-11):** Drei Korrekturen (#123).
>
> - Als Erzeuger stand hier `sdd dev pr`. Den Befehl gibt es seit SPEC-0044
>   nicht mehr.
> - Das Schema verlangte für `branch` das Muster `dev/SPEC-XXXX`. Die
>   Finalisierung übergibt aber ihren eigenen Branch, `feat/SPEC-XXXX` oder bei
>   `sdd distribute` `spec/SPEC-XXXX`, und genau der landet im Dokument. Jedes
>   Dokument, das heute entsteht, hätte das Schema verletzt. Das Muster und
>   INV-01 sind entsprechend angepasst.
> - Das `artifact`-Feld zeigte auf eine nie angelegte Schema-Datei und ist
>   entfernt.

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
      "minLength": 1,
      "description": "Branch, von dem der PR ausgeht: der von der Finalisierung übergebene (feat/SPEC-XXXX, bei sdd distribute spec/SPEC-XXXX); ohne Angabe dev/SPEC-XXXX"
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
      "example": "git checkout main && git merge feat/SPEC-0021"
    },
    "diff_stat": {
      "type": "string",
      "description": "Ausgabe von git diff main..<branch> --stat"
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

- **INV-01:** `branch` ist der Branch, den der Aufrufer übergibt. Bei der Finalisierung
  ist das `feat/SPEC-0021`. Ohne Angabe leitet die Strategie `dev/SPEC-0021` ab.
- **INV-02:** `test_result: passed` nur wenn `tests_passed == tests_total` und
  beide > 0.
- **INV-03:** `merge_command` enthält den Branch-Namen aus dem `branch`-Feld.
- **INV-04:** `.sdd/prs/` wird von der lokalen PR-Strategie automatisch erstellt, falls
  nicht vorhanden (analog zu `.sdd/pipeline/`).
