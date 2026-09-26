---
id: CON-0215
title: "Verweise, Entfernen, Config-Migration und ARCH-05"
type: behavior
format: gherkin
spec: SPEC-0062
version: 0.2.0
status: draft
artifact: ".sdd/contracts/behavior/verweise-entfernen-config-migration-und-arch-05.feature"
tests: ["TST-0244"]
---

# Contract: Verweise, Entfernen, Config-Migration und ARCH-05

> **Spec:** SPEC-0062 · **Typ:** Verhalten (Gherkin) · **Status:** draft

## Zweck

Legt fest, wie die alten Ausführungspfade verschwinden: Verweise statt Befehle, entfernte Module, die Übernahme von `task_routing` und `llm.local_llm` in Rollen-Profile, die Lifecycle-Schritte für SPEC-0045 und CON-0012 und die Architekturregel ARCH-05 (SPEC-0062 FR-05 bis FR-07, FR-09, FR-10).

## Garantien

Die Szenarien im Artifact (`.sdd/contracts/behavior/verweise-entfernen-config-migration-und-arch-05.feature`) sind **ausführbare Spezifikation**.
Jedes Szenario MUSS durch einen automatisierten Test (pytest) abgedeckt sein. Die Architekturregel wird über `sdd arch check` am echten Repository geprüft.

## Invarianten

- **INV-01:** `task-route`, `task-exec`, `task-loop` und `orchestrate` nehmen ihre bisherigen Argumente an, führen nichts aus (kein LLM-, Git- oder Dateizugriff), nennen den Ersatz mit den übergebenen IDs und enden mit Exit 1. In `sdd --help` erscheinen sie nicht.
- **INV-02:** Die Module `task_routing/`, `orchestrator.py` und `llm_probe.py` sowie die Symbole `get_code_gen_provider`, `CodeGenProvider`, `CodeGenResult`, `RecordingCodeGenProvider`, `ClaudeCliCodeGenProvider` und `OpenAICompatCodeGenProvider` existieren nicht mehr.
- **INV-03:** `sdd upgrade` übernimmt `llm.local_llm` als `llm.profiles.lokal` (provider, model, base_url, api_key) und ordnet bei `task_routing.enabled: true` die Stufen mit Score ≤ Schwelle (low = 15, medium = 50, high = 80) in `llm.roles.implementer.by_complexity` diesem Profil zu. Die übrigen Einträge von `config.yaml` bleiben unverändert.
- **INV-04:** Danach sind `task_routing` und `llm.local_llm` mit Präfix `# [SPEC-0062] ` auskommentiert; ihr Inhalt bleibt als Kommentar erhalten. Jede Änderung wird gemeldet. Ein zweiter Lauf ändert nichts.
- **INV-05:** Existiert `llm.profiles.lokal` oder `llm.roles.implementer.by_complexity` schon, wird nichts überschrieben und nichts auskommentiert; die Ausgabe nennt den Konflikt.
- **INV-06:** SPEC-0045 ist `deprecated` mit Nachfolger SPEC-0061, ebenso ihre Contracts CON-0171 bis CON-0174. CON-0012, CON-0024, CON-0033, CON-0063, CON-0113 und CON-0164 sind `deprecated` mit Grund. Die Config-Blöcke `llm.code_gen`, `llm.orchestrator` und `orchestrator` rührt die Migration nicht an.
- **INV-07:** `.sdd/architecture.yaml` enthält die Schicht `pipeline` (`tool/sdd_cli/pipeline/**`) und ARCH-05 mit ADR-0006: Außerhalb der Schichten `pipeline` und `entry` importiert kein Modul `pipeline.mediator`, `runner`, `steps`, `gates`, `providers`, `decisions` oder `context`. `sdd arch check` ist grün, die Baseline enthält keinen Eintrag mit `fixed_by` SPEC-0061 oder SPEC-0062.

## Begriffe

| Begriff | Definition |
|---------|------------|
| Verweis | Befehl, der nur auf seinen Ersatz hinweist und mit Exit 1 endet (Konvention SPEC-0058) |
| Schwelle | `task_routing.complexity_threshold`, Default 30 |
| Facade | öffentliche Pipeline-Module `monitor`, `store`, `schemas`, `roles`, `path_policy` und die CLI |
