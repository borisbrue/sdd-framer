---
id: CON-XXXX
project: ""                # PRJ-XXXX
title: "<API-Name>"
type: api
format: openapi
spec: SPEC-XXXX            # zugehörige Spec (Pflicht)
version: 0.1.0
status: draft              # draft | active | deprecated
artifact: "contracts/api/<name>.openapi.yaml"
tests: []                  # zugehörige Test-IDs
---

# Contract: {{title}}

> **Spec:** {{spec}} · **Typ:** API (OpenAPI) · **Status:** {{status}}

## Zweck

<!-- Was garantiert dieser Contract? Welche Spec-Anforderung deckt er ab? -->

## Geltungsbereich

- **In Scope:** ...
- **Out of Scope:** ...

## Verbindlichkeit

Dieser Contract ist **bindend**. Jede Implementierung MUSS:

1. das im Artifact (`{{artifact}}`) hinterlegte OpenAPI-Schema einhalten,
2. die Contract-Tests (siehe Frontmatter `tests:`) bestehen,
3. Breaking Changes nur mit Versions-Bump (MAJOR) und ADR einführen.

## Versionierung

Semantic Versioning für den Contract selbst:

- **MAJOR:** Breaking Change am Schema (z.B. Feld entfernt, Typ geändert)
- **MINOR:** Additiv (neues optionales Feld, neuer Endpoint)
- **PATCH:** Doku-/Beschreibungsänderungen

## Validierung

Der eigentliche Schema-Artifact liegt unter `{{artifact}}`. Validierung erfolgt durch:

- Schema-Linting (z.B. `spectral lint`)
- Contract-Tests gegen die Implementierung (z.B. `schemathesis`, `dredd`, `pact`)
