---
id: TST-0216
project: PRJ-0001
title: "GET /api/patterns – Response-Shape"
level: contract
spec: SPEC-0049
contract: CON-0184
status: planned
framework: pytest
artifact: "tests/contract/test_tst_0216.py"
tags: [api, patterns, web]
---

# Test: GET /api/patterns – Response-Shape

> **Level:** contract · **Spec:** SPEC-0049 · **Contract:** CON-0184 · **Status:** planned

## Was wird geprüft?

Der Endpunkt `GET /api/patterns` gegen das OpenAPI-Schema (FastAPI TestClient).

## Testfälle

- **test_returns_200_array:** Status 200, Body ist eine JSON-Liste (G-01).
- **test_item_shape:** jedes Element hat `pattern_name`, `specs[]` (mit `spec_id`+`reason`),
  `refactoring_guru_url` (string|null), `code_locations[]` (G-02/G-04).
- **test_only_accepted:** nur akzeptierte Patterns erscheinen – keine `suggested`/`rejected` (G-05).
- **test_empty_catalog_returns_empty_list:** leerer Katalog → `[]` (G-01).

## Abdeckung
CON-0184 G-01…G-05 · SPEC-0049 FR-01.
