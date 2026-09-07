---
id: HOL-XXXX
title: "<Szenario-Name>"
spec: SPEC-XXXX
contract: CON-XXXX
status: ready            # ready | active | disabled | wip
                         # ready und active werden evaluiert, wip und disabled nicht
                         # (SPEC-0033 FR-03; evaluator._EVAL_STATUSES)
priority: normal         # critical | normal | edge-case
type: http
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

<!-- Optionale Vorbereitungsschritte. Captured-Variablen stehen in ## Test als {captured.name} zur Verfügung. -->
<!-- Abschnitt entfernen wenn kein Setup nötig. -->

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
    method: GET          # GET | POST | PUT | PATCH | DELETE
    path: /api/<endpoint>/{captured.<variable>}
    # headers:
    #   Authorization: Bearer {captured.token}
    # body:
    #   key: value
  assert:
    status: 200
    body:
      # Skalar = exakter Match
      # {captured.var} = Variable aus Setup
      # { present: true } = Key muss vorhanden sein
      # { contains: "text" } = Teilstring-Prüfung
      data.ok: true
      data.id: "{captured.<variable>}"
```

## Teardown

<!-- Optionale Aufräumschritte (laufen auch bei Fehler). Entfernen wenn nicht nötig. -->

```yaml
- step: cleanup
  action:
    method: DELETE
    path: /api/<endpoint>/{captured.<variable>}
```

## Evaluation Hint

<!-- Struktur: (1) Welche Assertion kann fehlschlagen, (2) Wo im Code liegt die Ursache, (3) Welcher Task-Delta behebt es. -->

Wenn `status != <erwartet>`: ...
Wenn `data.<field>` fehlt: Prüfe `<module>.py:<funktion>()` — ...
Fix-Richtung: <Was muss der Task ändern>.
