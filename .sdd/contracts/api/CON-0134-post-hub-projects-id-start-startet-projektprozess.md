---
id: CON-0134
project: ""                # PRJ-XXXX
title: "POST /hub/projects/{id}/start startet Projektprozess"
type: api
format: openapi
spec: SPEC-0038
version: 0.1.0
status: draft              # draft | active | deprecated
artifact: ".sdd/contracts/api/post-hub-projects-id-start-startet-projektprozess.openapi.yaml"
tests: ["TST-0156"]                  # zugehörige Test-IDs
---

# Contract: POST /hub/projects/{id}/start startet Projektprozess

> **Spec:** SPEC-0038 · **Typ:** API (OpenAPI) · **Status:** draft

## Zweck

<!-- Was garantiert dieser Contract? Welche Spec-Anforderung deckt er ab? -->

## Geltungsbereich

- **In Scope:** ...
- **Out of Scope:** ...

## Verbindlichkeit

Dieser Contract ist **bindend**. Jede Implementierung MUSS:

1. das im Artifact (`.sdd/contracts/api/post-hub-projects-id-start-startet-projektprozess.openapi.yaml`) hinterlegte OpenAPI-Schema einhalten,
2. die Contract-Tests (siehe Frontmatter `tests:`) bestehen,
3. Breaking Changes nur mit Versions-Bump (MAJOR) und ADR einführen.

## Versionierung

Semantic Versioning für den Contract selbst:

- **MAJOR:** Breaking Change am Schema (z.B. Feld entfernt, Typ geändert)
- **MINOR:** Additiv (neues optionales Feld, neuer Endpoint)
- **PATCH:** Doku-/Beschreibungsänderungen

## Validierung

Der eigentliche Schema-Artifact liegt unter `.sdd/contracts/api/post-hub-projects-id-start-startet-projektprozess.openapi.yaml`. Validierung erfolgt durch:

- Schema-Linting (z.B. `spectral lint`)
- Contract-Tests gegen die Implementierung (z.B. `schemathesis`, `dredd`, `pact`)
