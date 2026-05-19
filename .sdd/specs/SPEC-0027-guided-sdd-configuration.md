---
id: SPEC-0027
title: Geführte SDD-Projektkonfiguration
status: in-progress
owner: Boris
created: 2026-05-19
updated: '2026-05-19'
version: 0.1.0
priority: high
tags:
- config
- wizard
- llm-pool
- docker
- cli
- ci-cd
depends_on:
- SPEC-0008
- SPEC-0026
- SPEC-0019
contracts:
- CON-0102
- CON-0103
- CON-0104
- CON-0105
- CON-0106
- CON-0107
tests:
- TST-0121
- TST-0122
- TST-0123
- TST-0124
- TST-0125
- TST-0126
adrs: []
started_at: '2026-05-19T13:14:40Z'
---
# Geführte SDD-Projektkonfiguration

> **Status:** draft · **Owner:** Boris · **Version:** 0.1.0

## 1. Kontext & Motivation

Die aktuelle SDD-Konfiguration liegt als reine YAML-Datei (`.sdd/config.yaml`) vor
und muss manuell editiert werden. Es gibt keine Validierung beim Schreiben, keine
geführte Einrichtung und keinen Überblick über den aktuellen Zustand. Besonders
der LLM-Pool (welche Provider, welche Modelle, welche API-Keys, welche
Auswahlstrategie) und die Container-Konfiguration (Ressourcenlimits,
Parallelität, Cleanup) sind komplex und fehleranfällig.

Ziel ist ein interaktiver `sdd config`-Befehl sowie ein Claude-Code-Skill
`/sdd-config`, der Neukonfiguration und Anpassungen sicher und geführt
durchführt — ohne dass der Nutzer YAML-Syntax kennen muss.

## 2. Zielsetzung

### Erfolgskriterien

- Nach dem Wizard ist `config.yaml` vollständig, valide und durch `sdd validate`
  bestätigt — kein manuelles YAML-Editing nötig
- Alle LLM-Provider (Anthropic, Ollama, OpenAI-compat, HuggingFace) können
  konfiguriert, getestet und priorisiert werden; beliebig viele Einträge möglich
- Docker/Podman-Konfiguration inkl. Ressourcenlimits und Parallelität
  ist über den Wizard vollständig einrichtbar
- `sdd config show` zeigt den aktuellen Zustand strukturiert an
- CI/CD kann die Config non-interaktiv setzen:
  `sdd config set llm.pool[0].api_key_env=ANTHROPIC_API_KEY --non-interactive`
- Neue Nutzer kommen nach `sdd init` automatisch in den Setup-Wizard

### Nicht-Ziele

- Kein GUI / Web-UI (separates Thema, SPEC-0003 Update)
- Kein eigenes Secret-Management — API-Keys kommen aus Env-Vars oder CI-Secrets,
  nie direkt in `config.yaml`
- Keine Migration alter Config-Formate
- Kein Multi-Projekt-Config-Management
- Kein Cluster-Orchestrierungssystem (kein Kubernetes, kein Swarm) —
  Docker/Podman lokal genügt

## 3. Architektur & Design Patterns

**Builder Pattern** (`ConfigWizard`): Schritt-für-Schritt-Führung durch alle
Konfigurationsabschnitte. Jeder Abschnitt ist ein eigenständiger Schritt mit
Validierung, Default-Vorschlägen und Rücksprung-Option. Das fertige
Config-Objekt wird erst am Ende in `config.yaml` geschrieben.
[Refactoring Guru – Builder](https://refactoring.guru/design-patterns/builder)

**Strategy Pattern** (`LlmProviderStrategy`): Jeder LLM-Provider (Anthropic,
Ollama, OpenAI-compat, HuggingFace) implementiert dieselbe Schnittstelle für
Verbindungstest, Key-Validierung und Capability-Abfrage. Neue Provider werden
als neue Strategien eingebunden, ohne den Wizard zu ändern.
[Refactoring Guru – Strategy](https://refactoring.guru/design-patterns/strategy)

**Command Pattern** (`sdd config set/get/show/test`): Jede Config-Operation
ist ein diskreter Befehl mit klarer Semantik, der auch non-interaktiv
(CI/CD) ausführbar ist.
[Refactoring Guru – Command](https://refactoring.guru/design-patterns/command)

## 4. Funktionale Anforderungen

### Wizard & CLI
- FR-01: `sdd config wizard` startet einen interaktiven geführten Setup für alle
  Config-Abschnitte (Projekt, LLM-Pool, Docker, Evaluator, Orchestrator,
  Validation). Jede Section ist einzeln ansteuerbar:
  `sdd config wizard --section llm`
- FR-02: `sdd config show [--section llm|docker|evaluator|...]` zeigt die
  aktuelle Konfiguration strukturiert und lesbar an
- FR-03: `sdd config set <key>=<value>` setzt einen einzelnen Wert
  non-interaktiv; validiert sofort nach dem Schreiben
- FR-04: `sdd config get <key>` liest einen einzelnen Wert aus
- FR-08: Nach `sdd init` wird der Wizard automatisch gestartet wenn
  `project.description` noch den Platzhalter enthält
- FR-09: CI/CD-Modus (`--non-interactive`): alle Wizard-Schritte können via
  Flags oder Env-Vars befüllt werden, kein interaktiver Prompt
- FR-11: `sdd config validate` prüft die gesamte Config auf Vollständigkeit,
  Konsistenz und Erreichbarkeit aller konfigurierten LLMs

### LLM-Pool
- FR-05: LLM-Pool-Konfiguration: beliebig viele Provider eintragen (id, type,
  model, cost_tier, max_context_tokens, api_key_env). Wizard führt durch jeden
  Eintrag und bietet Templates für bekannte Provider
- FR-06: `sdd config test-llm [--id <llm-id>]` sendet einen Ping-Prompt an
  den konfigurierten Provider und meldet Erreichbarkeit + Latenz
- FR-07: Wizard und `sdd config set` schreiben nie API-Keys direkt in
  `config.yaml` — nur Env-Var-Namen (z.B. `ANTHROPIC_API_KEY`)
- FR-12: LLM-Auswahlstrategie konfigurierbar: `cost_first` (günstigstes
  zuerst), `quality_first` (mächtigstes zuerst), `local_first` (Ollama
  bevorzugt)

### Container-Konfiguration
- FR-13: Wizard konfiguriert Docker-Runtime (docker/podman), Image-Name,
  Dockerfile-Pfad und optionale Registry (URL + Auth-Env-Var)
- FR-14: `docker.max_parallel_containers` konfigurierbar (Default: 2) —
  begrenzt gleichzeitige Container bei `sdd distribute` und `sdd finalize`
- FR-15: `docker.resources.cpu_limit` und `docker.resources.memory_limit`
  werden als Docker-Run-Flags weitergegeben (z.B. `"1.0"` CPU, `"1g"` RAM);
  Default: keine Limits
- FR-16: `docker.cleanup.on_success: true` / `on_failure: false` —
  Container nach Erfolg automatisch entfernen; bei Fehler für Debugging
  behalten. `skip_if_unavailable: false` erlaubt Fallback auf lokale Tests

### Claude-Code-Skill
- FR-10: `/sdd-config` Claude-Code-Skill: geführte Konfiguration direkt in
  Claude Code — liest aktuelle Config, zeigt Probleme, schlägt Änderungen
  vor und schreibt sie nach Bestätigung

## 5. User Stories

- Als **neuer SDD-Nutzer** möchte ich nach `sdd init` automatisch durch den
  Setup-Wizard geführt werden, damit ich sofort loslegen kann ohne YAML-Syntax
  zu kennen.
- Als **bestehender Nutzer** möchte ich mit `sdd config wizard --section llm`
  nur den LLM-Pool neu konfigurieren, ohne den Rest anzufassen.
- Als **CI/CD-Pipeline** möchte ich mit
  `sdd config set llm.pool[0].api_key_env=ANTHROPIC_API_KEY --non-interactive`
  die Config skriptgesteuert setzen, damit kein manueller Eingriff nötig ist.
- Als **Nutzer mit mehreren Providern** möchte ich Anthropic für komplexe Tasks
  und Ollama für einfache Tasks hinterlegen und die Auswahlstrategie auf
  `local_first` setzen, damit ich Kosten minimiere.
- Als **Entwickler** möchte ich mit `sdd config test-llm` sofort sehen ob mein
  Ollama-Server erreichbar ist, bevor ich `sdd distribute` starte.

## 6. Ziel-Konfigurationsstruktur (Auszug)

```yaml
llm_pool:
  strategy: local_first   # cost_first | quality_first | local_first
  providers:
    - id: ollama-mistral
      type: local
      model: mistral:7b
      cost_tier: cheap
      max_context_tokens: 32000
      base_url: http://localhost:11434
    - id: claude-sonnet
      type: remote
      model: claude-sonnet-4-6
      cost_tier: standard
      max_context_tokens: 200000
      api_key_env: ANTHROPIC_API_KEY

docker:
  runtime: docker
  image: sdd-dev:latest
  dockerfile: .sdd/Dockerfile
  max_parallel_containers: 2
  resources:
    cpu_limit: "1.0"
    memory_limit: "1g"
  cleanup:
    on_success: true
    on_failure: false
  registry:
    url: ''
    auth_env: ''
  skip_if_unavailable: false
```

## 7. Contracts

_(werden nach Spec-Bestätigung angelegt)_

## 8. Tests

_(werden nach Contract-Erstellung angelegt)_

## 9. Implementierungsreihenfolge

1. `tool/sdd_cli/config_manager.py` — Config-Lese/Schreib-Layer + Dot-Notation-Zugriff (FR-03/04/11)
2. `tool/sdd_cli/llm_probe.py` — LlmProviderStrategy-Implementierungen + Verbindungstest (FR-05/06)
3. `tool/sdd_cli/config_wizard.py` — Interaktiver Wizard mit Section-Routing (FR-01/08/09/13–16)
4. `tool/sdd_cli/main.py` — `sdd config` Command-Group (FR-02/03/04)
5. `.claude/commands/sdd-config.md` — Claude-Code-Skill `/sdd-config` (FR-10)

## 10. Offene Fragen

- Soll `sdd config wizard` die bestehende Config als Defaults laden oder
  bei Erstkonfiguration von vorne anfangen?
- Welche Sections sind im Wizard zwingend vs. optional überspringbar?
- Braucht die GUI (SPEC-0003) eine eigene Config-Seite — soll SPEC-0027
  dafür schon die Datenbasis legen?
- Sollte `docker.max_parallel_containers` automatisch aus `nproc` ermittelt
  werden (z.B. `nproc / 2`)?

## 11. Änderungshistorie

| Version | Datum | Änderung |
|---------|-------|----------|
| 0.1.0 | 2026-05-19 | Initiale Erstellung inkl. Container-Konfiguration |
