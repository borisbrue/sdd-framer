---
id: CON-0017
project: ""                # PRJ-XXXX
title: "Test Run Results API"
type: api
format: openapi
spec: SPEC-0006
version: 0.1.0
status: draft              # draft | active | deprecated
artifact: "contracts/api/test-run-results-api.openapi.yaml"
tests: ["TST-0017"]                  # zugehörige Test-IDs
---

# Contract: Test Run Results API

> **Spec:** SPEC-0006 · **Typ:** API (OpenAPI) · **Status:** draft

## Zweck

<!-- Was garantiert dieser Contract? Welche Spec-Anforderung deckt er ab? -->

## Geltungsbereich

- **In Scope:** ...
- **Out of Scope:** ...

## Verbindlichkeit

Dieser Contract ist **bindend**. Jede Implementierung MUSS:

1. das im Artifact (`contracts/api/test-run-results-api.openapi.yaml`) hinterlegte OpenAPI-Schema einhalten,
2. die Contract-Tests (siehe Frontmatter `tests:`) bestehen,
3. Breaking Changes nur mit Versions-Bump (MAJOR) und ADR einführen.

## Versionierung

Semantic Versioning für den Contract selbst:

- **MAJOR:** Breaking Change am Schema (z.B. Feld entfernt, Typ geändert)
- **MINOR:** Additiv (neues optionales Feld, neuer Endpoint)
- **PATCH:** Doku-/Beschreibungsänderungen

## Validierung

Der eigentliche Schema-Artifact liegt unter `contracts/api/test-run-results-api.openapi.yaml`. Validierung erfolgt durch:

- Schema-Linting (z.B. `spectral lint`)
- Contract-Tests gegen die Implementierung (z.B. `schemathesis`, `dredd`, `pact`)

## Erweiterung durch SPEC-0054

Mit einer Testsonde (`role: tests` in `.sdd/quality.yaml`) bekommt der Run-Report additiv die
optionalen Felder `junit`, `testcases` und `git_sha`; `runner` ist dann `probe:<name>`
(CON-0197 INV-05a/05b). Das OpenAPI-Artefakt dieses Contracts fehlt im Repo; bei seiner Erstellung
sind diese Felder aufzunehmen.
