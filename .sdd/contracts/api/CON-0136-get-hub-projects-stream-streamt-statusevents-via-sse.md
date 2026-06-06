---
id: CON-0136
project: ""                # PRJ-XXXX
title: "GET /hub/projects/stream streamt StatusEvents via SSE"
type: api
format: openapi
spec: SPEC-0038
version: 0.1.0
status: draft              # draft | active | deprecated
artifact: ".sdd/contracts/api/get-hub-projects-stream-streamt-statusevents-via-sse.asyncapi.yaml"
tests: ["TST-0158"]                  # zugehörige Test-IDs
---

# Contract: GET /hub/projects/stream streamt StatusEvents via SSE

> **Spec:** SPEC-0038 · **Typ:** API (OpenAPI) · **Status:** draft

## Zweck

<!-- Was garantiert dieser Contract? Welche Spec-Anforderung deckt er ab? -->

## Geltungsbereich

- **In Scope:** ...
- **Out of Scope:** ...

## Verbindlichkeit

Dieser Contract ist **bindend**. Jede Implementierung MUSS:

1. das im Artifact (`.sdd/contracts/api/get-hub-projects-stream-streamt-statusevents-via-sse.asyncapi.yaml`) hinterlegte OpenAPI-Schema einhalten,
2. die Contract-Tests (siehe Frontmatter `tests:`) bestehen,
3. Breaking Changes nur mit Versions-Bump (MAJOR) und ADR einführen.

## Versionierung

Semantic Versioning für den Contract selbst:

- **MAJOR:** Breaking Change am Schema (z.B. Feld entfernt, Typ geändert)
- **MINOR:** Additiv (neues optionales Feld, neuer Endpoint)
- **PATCH:** Doku-/Beschreibungsänderungen

## Validierung

Der eigentliche Schema-Artifact liegt unter `.sdd/contracts/api/get-hub-projects-stream-streamt-statusevents-via-sse.asyncapi.yaml`. Validierung erfolgt durch:

- Schema-Linting (z.B. `spectral lint`)
- Contract-Tests gegen die Implementierung (z.B. `schemathesis`, `dredd`, `pact`)
