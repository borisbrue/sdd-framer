---
id: SPEC-0052
title: config.yaml-Validator – Pflichtfelder, Provider-Werte, LLM-Routing-Konsistenz
type: feature
status: in-progress
owner: Boris
created: 2026-06-26
updated: '2026-06-26'
version: 0.1.0
priority: medium
tags:
- config
- validation
- llm
- cli
- dx
depends_on:
- SPEC-0008
- SPEC-0050
contracts:
- CON-0190
- CON-0191
tests:
- TST-0219
- TST-0220
fr_test_map:
  FR-01:
  - TST-0219
  FR-02:
  - TST-0219
  FR-03:
  - TST-0219
  FR-04:
  - TST-0219
  FR-05:
  - TST-0219
  FR-06:
  - TST-0220
  FR-07:
  - TST-0220
started_at: '2026-06-26T14:20:20Z'
---
# config.yaml-Validator – Pflichtfelder, Provider-Werte, LLM-Routing-Konsistenz

> **Status:** draft · **Owner:** Boris · **Version:** 0.1.0

## 1. Kontext & Motivation

`sdd init` erzeugt eine `config.yaml` mit sinnvollen Defaults, aber nach manuellen Anpassungen
(z.B. Einbinden eines lokalen LLM über `openai-compat`) passieren Fehler erst zur Laufzeit —
oft tief im Provider-Code mit kryptischen Tracebacks. Ein dedizierter Validator, der beim
`sdd validate`-Aufruf oder als CLI-Subcommand prüft, schließt diese Lücke:

- **Entwickler** nach `sdd init` oder manueller Config-Änderung bekommt sofort lesbares Feedback
- **CI/CD-Pipeline** kann `sdd config validate` als Gate vor dem ersten Run schalten
- **CLI-Nutzer** kennt den Fehler bevor er sich durch einen halben Analyse-Flow kämpft

## 2. Zielsetzung

### Erfolgskriterien
- Fehlende Pflichtfelder werden mit Feldpfad und Beschreibung gemeldet (`project.name fehlt`)
- Ungültige Provider-Werte (`provider: foobar`) werden erkannt und die erlaubte Menge angezeigt
- Provider-spezifische Pflichtfelder werden geprüft (`openai-compat` → `base_url` + `model`)
- Exit-Code 1 bei mindestens einem Fehler, Exit-Code 0 bei valider Config
- Ausgabe über `rich` mit farblicher Unterscheidung Error / Warning / OK

### Nicht-Ziele
- Kein automatisches Reparieren der Config (`--fix` ist nicht in Scope)
- Keine Validierung externer Ressourcen (ob LM Studio unter `base_url` erreichbar ist)
- Kein Schema-Migration zwischen Config-Versionen
- Keine Validierung von Env-Var-Inhalten (nur ob die Referenz auflösbar ist)

## 3. Architektur & Design Patterns

### Chain of Responsibility
Jede Validierungsregel ist ein eigenständiger Handler (`ConfigCheck`). Die Checks werden
sequenziell ausgeführt; jeder sammelt Fehler und gibt sie weiter — kein früher Abbruch.
So sind Checks unabhängig testbar und erweiterbar.

→ [Refactoring Guru: Chain of Responsibility](https://refactoring.guru/design-patterns/chain-of-responsibility)

**Begründung:** Die Config hat mehrere unabhängige Validierungsebenen (Struktur, Provider-Werte,
Provider-Konsistenz). Chain of Responsibility vermeidet ein monolithisches `if/elif`-Gebirge
und macht jeden Check einzeln testbar.

### Composite Pattern
Die Config-Struktur ist hierarchisch (`llm.completion`, `llm.orchestrator`, …). Ein
`CompositeCheck` gruppiert Provider-Checks unter einem Eltern-Check (`LlmSectionCheck`),
sodass die Fehlerpfade (`llm.completion.base_url`) automatisch aus dem Kontext aufgebaut werden.

→ [Refactoring Guru: Composite](https://refactoring.guru/design-patterns/composite)

**Begründung:** Vermeidet hartgecodete Pfadstrings in jedem Check; der Kontext wird
beim Traversieren der Config-Hierarchie automatisch akkumuliert.

## 4. Funktionale Anforderungen

- **FR-01** – Pflichtfeld-Check: `version`, `project.name`, `project.description` müssen gesetzt sein.
- **FR-02** – Provider-Enum-Check: Jedes `llm.<component>.provider` muss in
  `("anthropic", "claude-cli", "openai-compat", "huggingface")` liegen.
- **FR-03** – openai-compat-Konsistenz: Wenn `provider: openai-compat`, müssen `base_url` und
  `model` im selben Block oder im `completion`/`code_gen`-Default-Block gesetzt sein.
- **FR-04** – huggingface-Konsistenz: Wenn `provider: huggingface` und `hf_mode` ≠ `local`,
  muss `hf_token` oder `${HF_TOKEN}` (auflösbar) gesetzt sein.
- **FR-05** – anthropic-Konsistenz: Wenn `provider: anthropic`, muss `api_key` oder
  `${ANTHROPIC_API_KEY}` (auflösbar) gesetzt sein — Warning, kein Error (keyfreier Betrieb
  erlaubt).
- **FR-06** – CLI-Integration: `sdd config validate` gibt strukturierte Ausgabe und setzt
  Exit-Code korrekt.
- **FR-07** – Maschinenlesbare Ausgabe: `--json`-Flag gibt JSON-Array mit
  `{level, path, message}` aus.

## 5. User Stories

- Als **Entwickler** möchte ich nach einer Config-Änderung sofort wissen ob der LLM-Provider
  korrekt konfiguriert ist, ohne einen kompletten Analyse-Lauf starten zu müssen.
- Als **CI/CD-Pipeline** möchte ich `sdd config validate` als Pre-Run-Gate nutzen, damit
  fehlerhafte Configs nicht erst im Review-Schritt auffallen.

## 6. Contracts
*(werden nach Review ergänzt)*

## 7. Tests
*(werden nach Review ergänzt)*

## 8. Implementierungsreihenfolge

1. `tool/sdd_cli/config_validator.py` — `ConfigCheck`-Basis + Chain-Runner + Composite
2. Einzelne Checks: `RequiredFieldsCheck`, `ProviderEnumCheck`, `OpenAiCompatCheck`,
   `HuggingFaceCheck`, `AnthropicCheck`
3. `main.py` — `sdd config validate [--json]` CLI-Command
4. Unit-Tests für jeden Check isoliert
5. Integration-Test mit echter `config.yaml` (valide + fehlerhaft)

## 9. Offene Fragen

- [x] Soll `sdd validate` (der bestehende Struktur-Validator) den Config-Check automatisch
  einschließen, oder bleibt `sdd config validate` ein separater Subcommand? → **Separater Subcommand** (`sdd config validate`), kein Eingriff in den bestehenden `sdd validate`-Flow.

## 10. Änderungshistorie

| Version | Datum      | Autor | Änderung        |
|---------|------------|-------|-----------------|
| 0.1.0   | 2026-06-26 | Boris | Initiale Version |
