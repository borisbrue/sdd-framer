---
id: ADR-0004
title: "LLM-Zugriff nur über die Provider-Factory"
status: accepted
date: 2026-09-25
deciders: [Boris, Claude]
related_specs: [SPEC-0059, SPEC-0060]
supersedes: ""
enforced_by: [ARCH-03]
---

# ADR-0004: LLM-Zugriff nur über die Provider-Factory

## Status

accepted

## Kontext

SPEC-0008 führt Provider-Abstraktion und Factory ein, SPEC-0060 umhüllt jeden Provider der
Factory mit der Usage-Erfassung. Wer einen Provider direkt erzeugt, umgeht Konfiguration und
Erfassung.

## Optionen

### Option A: Provider nur über `llm/factory.py` erzeugen
- **Pro:** Konfiguration, Usage und Tests an einer Stelle
- **Contra:** neue Aufrufarten brauchen eine Factory-Funktion

### Option B: Direkte Instanziierung erlaubt
- **Pro:** flexibel
- **Contra:** Aufrufe fehlen in `token_usage`; so entstanden die Altlasten in `decompose.py`

## Entscheidung

Option A (Factory Method aus SPEC-0060). ARCH-03 (`forbidden_dependency`): nichts außerhalb von
`tool/sdd_cli/llm/**` importiert aus `tool/sdd_cli/llm/providers/**`. Die Pipeline bekommt ihre
Rollen-Provider über `get_role_provider` (SPEC-0059 FR-08).

## Folgen

Die Baseline hat für ARCH-03 keinen Eintrag.

Maschinell geprüft durch `ARCH-03` in `.sdd/architecture.yaml` (`sdd arch check`, Pre-Commit-Hook).
Bezug: AGENTS.md, Abschnitt „Architektur“.
