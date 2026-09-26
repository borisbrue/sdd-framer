---
id: TST-0245
title: "Run-Optionen, sdd-implement, Web-Adapter und Action"
level: acceptance
spec: SPEC-0062
contract: CON-0216
status: planned
framework: pytest
artifact: "tests/acceptance/test_con_0216.py"
tags: [pipeline]
---

# Test: Run-Optionen, sdd-implement, Web-Adapter und Action

> **Level:** acceptance · **Spec:** SPEC-0062 · **Contract:** CON-0216 · **Status:** planned

## Was wird geprüft?

Die Run-Optionen `--session`/`--steps` (inkl. Fehlerfälle), den Skill-Text von `/sdd-implement` in Repo und Blueprint, die Web-Route als Adapter (Format, dry_run, no_pr, abort, paused), `sdd start --auto` und die GitHub-Action-Vorlage.

## Vorbedingungen

- Temporäres SDD-Projekt über `sdd init`; LLM-Rollen gegen den Fake-LLM-Server aus `tests/`.
- Kein echter `claude`-, `gh`- oder Netzwerkaufruf.

## Verknüpfung mit Contract

Dieser Test prüft konkret folgende Punkte aus CON-0216:

- [ ] INV-01
- [ ] INV-02
- [ ] INV-03
- [ ] INV-04
- [ ] INV-05
- [ ] INV-06
- [ ] INV-07
