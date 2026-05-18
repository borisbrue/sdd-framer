---
id: SPEC-0026
title: LLM Task Distribution Engine
status: implemented
owner: Boris
created: 2026-05-18
updated: '2026-05-18'
version: 0.1.0
priority: high
tags:
- llm
- task-distribution
- container
- orchestration
- parallelization
depends_on:
- SPEC-0008
- SPEC-0014
- SPEC-0019
- SPEC-0020
contracts:
- CON-0095
- CON-0096
- CON-0097
- CON-0098
- CON-0099
- CON-0100
- CON-0101
tests:
- TST-0114
- TST-0115
- TST-0116
- TST-0117
- TST-0118
- TST-0119
- TST-0120
adrs: []
started_at: '2026-05-18T22:01:47Z'
---
# LLM Task Distribution Engine

> **Status:** draft · **Owner:** Boris · **Version:** 0.1.0

## 1. Kontext & Motivation

Heute implementiert ein einziges LLM (Claude) ein Spec sequenziell. Das skaliert
nicht, nutzt keine Spezialisierung verschiedener Modelle und liefert keinen
unabhängigen Qualitätsgegenchek. Ziel ist es, ein Spec in atomare Tasks
aufzuteilen, diese klassifiziert an einen Pool aus lokalen und remote LLMs zu
verteilen, die Ergebnisse automatisch zu prüfen und als sauberen PR zusammen-
zuführen – ohne manuellen Eingriff nach der initialen Freigabe.

## 2. Zielsetzung

### Erfolgskriterien
- Ein Spec wird durch Claude in klassifizierte Tasks zerlegt; Entwickler bestätigt die Liste
- Tasks werden anhand von Komplexität und Kontextgröße dem passenden LLM zugewiesen
- Jeder Task läuft in einem isolierten Container (ein oder mehrere Tasks pro Container)
- Fehlerhafte Tasks werden automatisch mit erweitertem Kontext wiederholt (max. 3 Versuche)
- Valide Ergebnisse landen als Commit auf einem Spec-Branch
- Am Ende existiert ein PR mit allen validierten Commits; Tests laufen grün durch
- Spec-Status wechselt automatisch auf `implemented`; Container werden entfernt

### Nicht-Ziele
- Kein eigenes LLM-Training oder Fine-Tuning
- Keine manuelle Task-Bearbeitung durch Menschen (nur LLMs führen aus)
- Kein Multi-Repo-Support (immer das aktuelle SDD-Projekt)
- Kein eigenes Container-Orchestrierungssystem (Docker/Podman genügt, kein Kubernetes)

## 3. Architektur & Design Patterns

**Mediator Pattern** (`SddOrchestrator`): Der Orchestrator vermittelt zwischen
Spec-Dekomposition, LLM-Pool, Containern und Git. Keine Komponente kennt eine
andere direkt – sie kommunizieren nur über den Orchestrator. Das hält die
Erweiterbarkeit (neues LLM, neues Container-Backend) offen.
[Refactoring Guru – Mediator](https://refactoring.guru/design-patterns/mediator)

**Strategy Pattern** (`LlmSelector`): Die Auswahl des LLM für einen Task ist
eine austauschbare Strategie (z.B. `CheapFastStrategy` für einfache Tasks,
`PowerfulStrategy` für komplexe). Neue LLM-Backends aus SPEC-0008 werden als
neue Strategien eingebunden.
[Refactoring Guru – Strategy](https://refactoring.guru/design-patterns/strategy)

**State Pattern** (`TaskLifecycle`): Jeder Task durchläuft definierte Zustände:
`pending → assigned → running → review → passed | failed → committed | retrying`.
Ungültige Übergänge sind strukturell unmöglich.
[Refactoring Guru – State](https://refactoring.guru/design-patterns/state)

**Chain of Responsibility** (`ReviewPipeline`): Das Task-Ergebnis durchläuft
eine Kette von Checks (Syntax-Check → Unit-Tests → Claude-Code-Review). Jeder
Schritt kann abbrechen und einen Retry auslösen.
[Refactoring Guru – Chain of Responsibility](https://refactoring.guru/design-patterns/chain-of-responsibility)

## 4. Funktionale Anforderungen

- FR-01: `sdd decompose SPEC-XXXX` – Claude zerlegt Spec in atomare Tasks (Titel, Beschreibung, geschätzte Tokengröße, Typ: code/test/config/doc)
- FR-02: Entwickler prüft und bestätigt Task-Liste interaktiv vor der Verteilung
- FR-03: Tasks werden klassifiziert: Komplexität (low/medium/high), Kontextgröße (S/M/L), Typ
- FR-04: LLM-Pool-Registry: konfigurierbare Liste aus lokalen (Ollama) und remote (Anthropic, OpenAI) LLMs mit Capabilities
- FR-05: `LlmSelector` wählt anhand Task-Klassifizierung das passende LLM automatisch aus
- FR-06: Pro Spec wird ein dedizierter Git-Branch `spec/SPEC-XXXX` angelegt
- FR-07: Docker/Podman-Container mit aktuellem Code-Stand wird erzeugt; ein oder mehrere Tasks werden einem Container zugewiesen
- FR-08: LLM erhält Task-Kontext (Spec-Abschnitt, relevante Dateien, bestehende Tests) und führt Implementierung durch
- FR-09: `ReviewPipeline` prüft Ergebnis automatisch (Syntax → Tests → Claude-Review)
- FR-10: Positive Prüfung → Commit auf Spec-Branch; negativ → Retry mit erweitertem Kontext (max. 3 Versuche)
- FR-11: Nach 3 fehlgeschlagenen Versuchen wird Task als `blocked` markiert und Entwickler wird benachrichtigt
- FR-12: Sind alle Tasks `committed`, wird ein PR von `spec/SPEC-XXXX` gegen `main` erstellt
- FR-13: Test-Suite wird automatisch auf dem PR ausgeführt
- FR-14: Bei grünen Tests wird PR in `main` gemergt
- FR-15: Spec-Status wird auf `implemented` gesetzt
- FR-16: Container werden nach Abschluss (oder Abbruch) entfernt

## 5. User Stories

- Als Entwickler möchte ich `sdd decompose SPEC-0026` aufrufen und eine bestätigbare Task-Liste erhalten, damit ich den Verteilungsplan vor der Ausführung kontrollieren kann.
- Als Solo-Entwickler möchte ich, dass einfache Tasks (low/S) automatisch an günstige/lokale LLMs gehen, damit ich Kosten spare.
- Als Entwickler möchte ich bei blockierten Tasks eine klare Benachrichtigung mit dem Fehlerkontext erhalten, damit ich gezielt eingreifen kann.
- Als Entwickler möchte ich am Ende einen fertigen PR vorfinden, ohne manuell Commits zusammenführen zu müssen.

## 6. Contracts

_(werden nach Spec-Bestätigung angelegt)_

## 7. Tests

_(werden nach Contract-Erstellung angelegt)_

## 8. Implementierungsreihenfolge

1. `tool/sdd_cli/decompose.py` – Task-Dekomposition via Claude (FR-01/02/03)
2. `tool/sdd_cli/llm_pool.py` – LLM-Pool-Registry + LlmSelector (FR-04/05)
3. `tool/sdd_cli/container.py` – Container-Lifecycle (FR-07/16)
4. `tool/sdd_cli/task_runner.py` – Task-Ausführung + ReviewPipeline (FR-08/09/10/11)
5. `tool/sdd_cli/orchestrator.py` – SddOrchestrator als Mediator (FR-06/12/13/14/15)
6. `tool/sdd_cli/main.py` – CLI-Commands `sdd decompose` + `sdd distribute` + `sdd task-status`

## 9. Offene Fragen

- Wie wird der Container-Snapshot erstellt? (git archive vs. docker build from current state)
- Maximale Parallelität: Wie viele Container gleichzeitig? Konfigurierbar?
- `sdd orchestrate` (zukünftig, SPEC-0027?) – übergeordneter Workflow, der mehrere SPEC-Verteilungen koordiniert
- Benachrichtigungskanal für blockierte Tasks: CLI-Output genügt zunächst, oder auch SPEC-0012 (MQTT/WebSocket)?

## 10. Änderungshistorie

| Version | Datum | Änderung |
|---|---|---|
| 0.1.0 | 2026-05-18 | Initiale Erstellung |
