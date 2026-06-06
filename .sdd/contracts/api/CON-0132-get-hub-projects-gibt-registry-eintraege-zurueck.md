---
id: CON-0132
project: ""                # PRJ-XXXX
title: "GET /hub/projects gibt Registry-Einträge zurück"
type: api
format: openapi
spec: SPEC-0038
version: 0.1.0
status: draft              # draft | active | deprecated
artifact: ".sdd/contracts/api/get-hub-projects-gibt-registry-eintraege-zurueck.openapi.yaml"
tests: ["TST-0154"]                  # zugehörige Test-IDs
---

# Contract: GET /hub/projects gibt Registry-Einträge zurück

> **Spec:** SPEC-0038 · **Typ:** API (OpenAPI) · **Status:** draft

## Zweck

<!-- Was garantiert dieser Contract? Welche Spec-Anforderung deckt er ab? -->

## Geltungsbereich

- **In Scope:** ...
- **Out of Scope:** ...

## Verbindlichkeit

Dieser Contract ist **bindend**. Jede Implementierung MUSS:

1. das im Artifact (`.sdd/contracts/api/get-hub-projects-gibt-registry-eintraege-zurueck.openapi.yaml`) hinterlegte OpenAPI-Schema einhalten,
2. die Contract-Tests (siehe Frontmatter `tests:`) bestehen,
3. Breaking Changes nur mit Versions-Bump (MAJOR) und ADR einführen.

## Versionierung

Semantic Versioning für den Contract selbst:

- **MAJOR:** Breaking Change am Schema (z.B. Feld entfernt, Typ geändert)
- **MINOR:** Additiv (neues optionales Feld, neuer Endpoint)
- **PATCH:** Doku-/Beschreibungsänderungen

## Validierung

Der eigentliche Schema-Artifact liegt unter `.sdd/contracts/api/get-hub-projects-gibt-registry-eintraege-zurueck.openapi.yaml`. Validierung erfolgt durch:

- Schema-Linting (z.B. `spectral lint`)
- Contract-Tests gegen die Implementierung (z.B. `schemathesis`, `dredd`, `pact`)
