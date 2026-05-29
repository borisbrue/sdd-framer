---
id: CON-0110
project: PRJ-0001
title: Contract- und Holdout-Inline-Editor API
type: api
format: markdown
spec: SPEC-0028
version: 0.1.0
status: review
tests:
- TST-0129
---
# Contract: Contract- und Holdout-Inline-Editor API

## Garantie

Contracts und Holdouts können über REST gelesen, überschrieben und mit KI-Hilfestellung bearbeitet werden. Schreiboperationen sind atomisch (vollständige Datei wird überschrieben).

## Endpunkte

### GET /api/specs/{spec_id}/contracts/{con_id}

Response: `{id, frontmatter: {}, body: str, path: str}`

### PUT /api/specs/{spec_id}/contracts/{con_id}

Request: `{body: str}`
Response: `{ok: true, id: str}`

### POST /api/specs/{spec_id}/contracts/{con_id}/assist

Request: `{question: str, context?: str}`
Response: `{ok: bool, output: str}` — LLM-generierte Hilfestellung

### GET /api/specs/{spec_id}/holdouts/{hol_id}

Response: `{id, frontmatter: {}, body: str, path: str}`

### PUT /api/specs/{spec_id}/holdouts/{hol_id}

Request: `{body: str}`
Response: `{ok: true, id: str}`

### POST /api/specs/{spec_id}/holdouts/{hol_id}/assist

Request: `{question: str, context?: str}`
Response: `{ok: bool, output: str}` — Nur Contract-Kontext, kein Sourcecode

## Fehlerbedingungen

| Bedingung | HTTP-Code |
|-----------|-----------|
| Contract/Holdout nicht gefunden | 404 |
| LLM-Fehler bei assist | 200, ok: false |
