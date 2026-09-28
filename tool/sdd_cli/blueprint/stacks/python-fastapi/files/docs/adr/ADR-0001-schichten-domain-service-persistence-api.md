---
id: ADR-0001
title: "Schichten domain, service, persistence, api"
status: accepted
date: 2026-09-27
deciders: [{{project_name}}]
related_specs: []
supersedes: ""
enforced_by: [ARCH-01]
---

# ADR-0001: Schichten domain, service, persistence, api

## Status

accepted

## Kontext

Die Vorlage python-fastapi trennt Fachlogik (domain), Anwendungsfälle (service), Speicherung
(persistence) und HTTP-Schnittstelle (api), damit jede Schicht einzeln testbar bleibt.

## Entscheidung

`api` nutzt nur `service` und `domain`; `service` nur `domain`; `persistence` nur `domain`.
`{{package_name}}/__init__.py` und `__main__.py` verdrahten die Schichten.

## Folgen

Maschinell geprüft durch ARCH-01 in `.sdd/architecture.yaml` (`sdd arch check`).
