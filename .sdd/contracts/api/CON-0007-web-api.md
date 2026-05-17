---
id: CON-0007
title: "web-api"
type: api
format: openapi
spec: SPEC-0003
version: 0.1.0
status: draft              # draft | active | deprecated
artifact: "contracts/api/web-api.openapi.yaml"
tests: [TST-0008]
---

# Contract: web-api

> **Spec:** SPEC-0003 · **Typ:** API (OpenAPI) · **Status:** draft

## Zweck

<!-- Was garantiert dieser Contract? Welche Spec-Anforderung deckt er ab? -->

## Geltungsbereich

- **In Scope:** ...
- **Out of Scope:** ...

## Verbindlichkeit

Dieser Contract ist **bindend**. Jede Implementierung MUSS:

1. das im Artifact (`contracts/api/web-api.openapi.yaml`) hinterlegte OpenAPI-Schema einhalten,
2. die Contract-Tests (siehe Frontmatter `tests:`) bestehen,
3. Breaking Changes nur mit Versions-Bump (MAJOR) und ADR einführen.

## Versionierung

Semantic Versioning für den Contract selbst:

- **MAJOR:** Breaking Change am Schema (z.B. Feld entfernt, Typ geändert)
- **MINOR:** Additiv (neues optionales Feld, neuer Endpoint)
- **PATCH:** Doku-/Beschreibungsänderungen

## Validierung

Der eigentliche Schema-Artifact liegt unter `contracts/api/web-api.openapi.yaml`. Validierung erfolgt durch:

- Schema-Linting (z.B. `spectral lint`)
- Contract-Tests gegen die Implementierung (z.B. `schemathesis`, `dredd`, `pact`)
