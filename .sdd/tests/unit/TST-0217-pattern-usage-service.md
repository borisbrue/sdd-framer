---
id: TST-0217
project: PRJ-0001
title: "PatternUsageService – Scan, Normalisierung, Merge"
level: unit
spec: SPEC-0049
contract: CON-0185
status: planned
framework: pytest
artifact: "tests/unit/test_tst_0217.py"
tags: [patterns, scanner, merge]
---

# Test: PatternUsageService – Scan, Normalisierung, Merge

> **Level:** unit · **Spec:** SPEC-0049 · **Contract:** CON-0185 · **Status:** planned

## Was wird geprüft?

Der Code-Annotation-Scanner + Merge des `PatternUsageService` (Katalog-Quelle + Code-Quelle).

## Testfälle

- **test_accepted_pattern_with_annotation_has_location:** akzeptiertes Pattern mit Docstring-
  Annotation → `code_locations` mit file+line (CON-0185 Szenario 1).
- **test_accepted_pattern_without_annotation_empty_locations:** akzeptiert, keine Annotation →
  leere `code_locations` (INV-03).
- **test_name_normalization:** „Chain of Responsibility"-Annotation wird `ChainOfResponsibility`
  zugeordnet (Leerzeichen entfernt + lowercase, INV-02/FR-04).
- **test_orphan_annotation_ignored:** Annotation ohne Katalogeintrag wird verworfen (INV-03/FR-05).
- **test_empty_catalog_empty_result:** leerer Katalog → leere Aggregation.

## Abdeckung
CON-0185 INV-01…INV-05 · SPEC-0049 FR-02, FR-03, FR-04, FR-05.
