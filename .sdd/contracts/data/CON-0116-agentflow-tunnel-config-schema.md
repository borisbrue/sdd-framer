---
id: CON-0116
project: ""                # PRJ-XXXX
title: "AgentFlow Tunnel Config Schema"
type: data
format: json-schema
spec: SPEC-0032
version: 0.1.0
status: active
artifact: ".sdd/contracts/data/agentflow-tunnel-config-schema.schema.json"
tests: ["TST-0135"]
---

# Contract: AgentFlow Tunnel Config Schema

> **Spec:** SPEC-0032 · **Typ:** Daten (JSON Schema) · **Status:** draft

## Zweck

Beschreibt das Schema der `tunnel`-Sektion in `.sdd/config.yaml` (SPEC-0032 FR-08).
Wird beim PWA-Onboarding (SPEC-0025 QR-Code) gelesen, damit die PWA weiß,
unter welcher öffentlichen HTTPS-URL sie den SDD-Server erreicht.

## Invarianten

- **INV-01:** `tunnel.url` muss eine gültige URI sein und mit `https://` beginnen — kein HTTP, kein leerer String.
- **INV-02:** `tunnel.url` endet ohne trailing slash (PWA konkateniert Pfade direkt).
- **INV-03:** Das `tunnel`-Objekt erlaubt keine zusätzlichen Properties (additionalProperties: false).

## Beispiele

**Gültig:**
```yaml
tunnel:
  url: https://sdd.example.com
```

```yaml
tunnel:
  url: https://my-sdd.trycloudflare.com
```

**Ungültig (und warum):**
```yaml
tunnel:
  url: http://sdd.example.com
```
→ Verstößt gegen INV-01 (kein HTTPS).

```yaml
tunnel:
  url: https://sdd.example.com/
```
→ Verstößt gegen INV-02 (trailing slash).

## Validierung

- Schema unter `.sdd/contracts/data/agentflow-tunnel-config-schema.schema.json` (JSON Schema Draft 2020-12)
- Validatoren je nach Sprache: `ajv` (JS), `jsonschema` (Python), etc.
