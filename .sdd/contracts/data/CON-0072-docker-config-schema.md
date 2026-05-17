---
id: CON-0072
title: "docker-config-schema"
type: data
format: json-schema
spec: SPEC-0022
version: 0.1.0
status: draft
artifact: "contracts/data/docker-config.schema.json"
tests: [TST-0081]
---

# Contract: docker-config-schema

> **Spec:** SPEC-0022 · **Typ:** Daten (JSON Schema) · **Status:** draft

## Zweck

Definiert das vollständige Schema des `docker:`-Namespace in `.sdd/config.yaml`
für SPEC-0022. Erweitert den in SPEC-0021 eingeführten `docker:`-Block.

## Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "SDD docker: config namespace",
  "type": "object",
  "properties": {
    "runtime": {
      "type": "string",
      "enum": ["docker", "podman"],
      "default": "docker",
      "description": "Container-Runtime"
    },
    "image": {
      "type": "string",
      "default": "sdd-dev:latest",
      "description": "Image-Name inkl. Tag"
    },
    "dockerfile": {
      "type": "string",
      "default": ".sdd/Dockerfile",
      "description": "Pfad zum Dockerfile (relativ zum Projekt-Root)"
    },
    "registry": {
      "type": "object",
      "properties": {
        "url": {
          "type": "string",
          "default": "",
          "description": "Registry-URL, leer = kein Push"
        },
        "auth_env": {
          "type": "string",
          "default": "",
          "description": "Env-Var-Name mit Registry-Credentials"
        }
      }
    },
    "compose_file": {
      "type": "string",
      "default": "",
      "description": "Pfad zu docker-compose.yml, leer = kein Compose"
    },
    "log_stream": {
      "type": "object",
      "properties": {
        "enabled": {
          "type": "boolean",
          "default": true
        },
        "max_lines": {
          "type": "integer",
          "minimum": 1,
          "maximum": 10000,
          "default": 500
        }
      }
    }
  }
}
```

## Invarianten

- **INV-01:** `runtime` darf nur `docker` oder `podman` sein — andere Werte
  führen zu einem Validierungsfehler beim Start.
- **INV-02:** Alle Felder haben sinnvolle Defaults — eine minimale Config
  (`docker: {}`) ist valide.
- **INV-03:** `log_stream.max_lines` ist auf 1–10000 beschränkt.
