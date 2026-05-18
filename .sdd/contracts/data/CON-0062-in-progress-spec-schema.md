---
id: CON-0062
title: "in-progress-spec-schema"
type: data
format: json-schema
spec: SPEC-0019
version: 0.1.0
status: draft
artifact: ""
tests: [TST-0071]
---

# Contract: In-Progress Spec – Frontmatter-Schema

> **Spec:** SPEC-0019 · **Typ:** Data · **Status:** draft

## Zweck

Definiert das Frontmatter-Schema einer Spec im `in-progress`-Status.

## Pflichtfelder

- `status: in-progress`
- `updated`: Aktuelles Datum (ISO 8601)
- `contracts`: Mindestens ein CON-ID-Eintrag
