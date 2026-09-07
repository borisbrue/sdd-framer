---
id: HOL-XXXX
title: "<Szenario-Name>"
spec: SPEC-XXXX
contract: CON-XXXX
status: ready            # ready | active | disabled | wip
                         # ready und active werden evaluiert, wip und disabled nicht
                         # (SPEC-0033 FR-03; evaluator._EVAL_STATUSES)
priority: normal         # critical | normal | edge-case
type: cli
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

<!-- Optionale Vorbereitungsschritte (z.B. Dateien anlegen, Umgebung vorbereiten). -->
<!-- Abschnitt entfernen wenn kein Setup nötig. -->

```yaml
- step: <schritt_name>
  action:
    builtin: write_file
    path: /workspace/.sdd/specs/SPEC-TEST.md
    content: |
      ---
      id: SPEC-TEST
      ---
```

## Test

```yaml
test:
  action:
    command: sdd
    args: [<subcommand>, <argument>]
    cwd: /workspace         # default, kann weggelassen werden
    # env:
    #   SDD_ENV: test
  assert:
    exit_code: 0            # 0 = Erfolg, 1 = Fehler
    stdout_contains:
      - "<erwarteter Text>"
    # stdout_not_contains:
    #   - "<unerwünschter Text>"
    # stderr_empty: true
```

## Teardown

<!-- Aufräumen nach dem Test (laufen auch bei Fehler). Entfernen wenn nicht nötig. -->

```yaml
- step: cleanup
  action:
    builtin: delete_file
    path: /workspace/.sdd/specs/SPEC-TEST.md
```

## Evaluation Hint

<!-- Struktur: (1) Welche Assertion kann fehlschlagen, (2) Wo im Code liegt die Ursache, (3) Welcher Task-Delta behebt es. -->

Wenn `exit_code != 0`: ...
Wenn stdout `<text>` fehlt: Prüfe `<module>.py:<funktion>()` — ...
Fix-Richtung: <Was muss der Task ändern>.
