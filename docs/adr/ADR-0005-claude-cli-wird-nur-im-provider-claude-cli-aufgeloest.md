---
id: ADR-0005
title: "Claude-CLI wird nur im Provider claude_cli aufgelöst"
status: accepted
date: 2026-09-25
deciders: [Boris, Claude]
related_specs: [SPEC-0059]
supersedes: ""
enforced_by: [ARCH-04]
---

# ADR-0005: Claude-CLI wird nur im Provider claude_cli aufgelöst

## Status

accepted

## Kontext

sdd-framer läuft keyfrei über die `claude`-CLI. Wo sie gestartet wird, entscheidet über
Timeouts, Envelope-Auswertung und Usage-Erfassung. Der Programmpfad ist im Code immer eine Variable;
erkennbar ist nur, wo `shutil.which("claude")` ihn auflöst.

## Optionen

### Option A: Auflösen und Starten nur in `llm/providers/claude_cli.py`
- **Pro:** Envelope, Usage und Timeouts einheitlich
- **Contra:** Verfügbarkeitsprüfungen brauchen eine Funktion der Factory

### Option B: Freie Nutzung der CLI
- **Pro:** schnell
- **Contra:** Aufrufe ohne Usage und mit eigener Fehlerbehandlung

## Entscheidung

Option A. ARCH-04 (`forbidden_call`): `shutil.which` mit dem Argument `claude` nur in
`tool/sdd_cli/llm/providers/claude_cli.py`.

## Folgen

`local_agent.py` und zwei Verfügbarkeitsprüfungen der Web-API stehen in der Baseline; SPEC-0058
behebt sie.

Maschinell geprüft durch `ARCH-04` in `.sdd/architecture.yaml` (`sdd arch check`, Pre-Commit-Hook).
Bezug: AGENTS.md, Abschnitt „Architektur“.
