---
id: CON-0184
project: PRJ-0001
title: "GET /api/patterns – Pattern-Usage-Endpunkt"
type: api
format: openapi
spec: SPEC-0049
version: 0.1.0
status: approved
artifact: "contracts/api/pattern-usage-endpoint.openapi.yaml"
tests: [TST-0216, TST-0218]
---

# Contract: GET /api/patterns – Pattern-Usage-Endpunkt

> **Spec:** SPEC-0049 · **Typ:** API (OpenAPI) · **Status:** draft

## Zweck

Definiert den read-only HTTP-Endpunkt, über den die Web-UI die projektweit akzeptierten
Design-Patterns samt Code-Fundstellen abruft (FR-01, FR-02).

## Geltungsbereich

- **In Scope:** Response-Shape von `GET /api/patterns`; Aggregation Katalog → Response.
- **Out of Scope:** Scan-/Merge-Verhalten (→ CON-0185); Schreiboperationen; Auth (folgt dem
  bestehenden API-Rahmen aus SPEC-0003).

## Verbindlichkeit

Jede Implementierung MUSS:

1. das Schema aus `contracts/api/pattern-usage-endpoint.openapi.yaml` einhalten,
2. ausschließlich Patterns mit Status `accepted` zurückgeben,
3. die Contract-Tests (Frontmatter `tests:`) bestehen.

## Garantien

- **G-01:** Antwort ist immer ein JSON-Array (HTTP 200), auch bei leerem Katalog → `[]`.
- **G-02:** Jedes Array-Element enthält `pattern_name`, `specs[]` (`spec_id` + `reason`),
  `refactoring_guru_url` (string oder `null`) und `code_locations[]`.
- **G-03:** `specs` bündelt alle Specs, die dasselbe Pattern akzeptiert haben (Gruppierung
  nach `pattern_name`).
- **G-04:** `code_locations` ist ein Array (kann leer sein); jedes Element hat `file`
  (repo-relativ), `line` (1-basiert, ≥ 1) und `annotation` (getrimmt).
- **G-05:** `suggested`- und `rejected`-Patterns erscheinen NICHT in der Antwort.

## Versionierung

Semantic Versioning: MAJOR bei Breaking Change am Schema, MINOR additiv, PATCH für Doku.

## Validierung

Schema-Artifact: `contracts/api/pattern-usage-endpoint.openapi.yaml`.
Contract-Test prüft Statuscode, Array-Typ und die Pflichtfelder pro Element.
