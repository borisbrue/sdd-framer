---
id: TST-0214
project: PRJ-0001
title: "sdd init Autonomie-Provisioning"
level: unit
spec: SPEC-0051
contract: CON-0188
status: planned
framework: pytest
artifact: "tests/unit/test_tst_0214.py"
tags: [sdd-init, settings, autonomy]
---

# Test: sdd init Autonomie-Provisioning

> **Level:** unit · **Spec:** SPEC-0051 · **Contract:** CON-0188 · **Status:** planned

## Was wird geprüft?

Die Datei-/Settings-Effekte von `init_project()` (`tool/sdd_cli/init.py`) für das Autonomie-Setup.

## Testfälle

- **test_init_installs_guardrail_hook:** nach `sdd init` existiert `.claude/hooks/autonomous-guardrail.sh`
  und `.claude/settings.json` hat einen PreToolUse/Bash-Hook darauf (INV-01).
- **test_hook_merge_idempotent:** zweites `sdd init` erzeugt kein Hook-Duplikat; `permissions.allow`
  bleibt unverändert (INV-02).
- **test_no_autonomous_no_default_mode:** `sdd init` ohne `--autonomous` setzt kein `defaultMode`
  und legt keine `settings.local.json` mit Bypass an (INV-03).
- **test_autonomous_writes_local_only:** `sdd init --autonomous` schreibt
  `permissions.defaultMode=bypassPermissions` in `.claude/settings.local.json`, ergänzt `.gitignore`,
  und lässt committed `settings.json` ohne `defaultMode` (INV-04).

## Abdeckung

CON-0188 INV-01…INV-04 · SPEC-0051 FR-01, FR-02, FR-03.
