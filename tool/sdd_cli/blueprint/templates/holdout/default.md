---
id: HOL-XXXX
title: "<Szenario-Name>"
spec: SPEC-XXXX
contract: CON-XXXX
status: wip              # active | disabled | wip
priority: normal         # critical | normal | edge-case
type: http               # http | cli  →  Detailtemplates: holdout/http.md | holdout/cli.md
created: YYYY-MM-DD
updated: YYYY-MM-DD
tags: []
---

# Holdout: {{title}}

> **Contract:** {{contract}} · **Spec:** {{spec}} · **Priority:** {{priority}}
>
> ⚠️ Dieses Dokument ist dem Code-generierenden Agenten **nicht** zugänglich.

## Beschreibung

<!-- Was soll das System in diesem Szenario tun? Plain English, kein Code. -->

## Setup

<!-- Vorbereitungsschritte. Captured-Variablen stehen in ## Test als {captured.name} zur Verfügung. -->
<!-- Abschnitt entfernen wenn kein Setup nötig. Vollständiges Beispiel: holdout/http.md -->

```yaml
- step: <schritt_name>
  action:
    method: POST
    path: /api/<endpoint>
    body:
      <key>: <value>
  capture:
    <variable>: data.<json_path>
```

## Test

```yaml
test:
  action:
    method: GET
    path: /api/<endpoint>
  assert:
    status: 200
    body:
      data.ok: true
```

## Evaluation Hint

<!-- (1) Welche Assertion kann fehlschlagen → (2) Wo im Code → (3) Welcher Task-Delta behebt es. -->

Wenn `status != <erwartet>`: ...
Wenn `data.<field>` fehlt: Prüfe `<module>.py:<funktion>()` — ...
Fix-Richtung: <Was muss der Task ändern>.
