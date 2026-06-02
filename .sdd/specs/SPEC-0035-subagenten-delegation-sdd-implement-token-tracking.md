---
id: SPEC-0035
title: "Sub-Agenten-Delegation in sdd-implement mit Token-Tracking pro Task"
type: feature
status: draft
owner: "borisbrue"
created: 2026-06-02
updated: 2026-06-02
version: 0.1.0
priority: medium
tags: ["agent-sdk", "token-tracking", "sdd-implement", "claude-specific"]
depends_on: ["SPEC-0011", "SPEC-0032"]
contracts: []
tests: []
adrs: []
---

# Sub-Agenten-Delegation in sdd-implement mit Token-Tracking pro Task

> **Status:** draft · **Owner:** borisbrue · **Version:** 0.1.0

## 1. Kontext & Motivation

Der `sdd-implement`-Skill führt heute alle Tasks einer Spec sequenziell in einem
einzigen Claude-Kontext aus. Das hat drei Konsequenzen:

1. **Token-Verbrauch nicht messbar:** `sdd calibrate` kann nur den Gesamt-Verbrauch
   einer Session erfassen — welcher Task wie viele Tokens gekostet hat, ist unsichtbar.
2. **Kontext-Drift:** Bei umfangreichen Specs akkumuliert sich Gesprächs-Kontext über
   alle Tasks hinweg. Spätere Tasks "sehen" die Outputs früherer Tasks, was zu
   ungewollter Beeinflussung und erhöhtem Token-Verbrauch führt.
3. **Fehler-Isolation fehlt:** Ein fehlschlagender Task reißt die gesamte Session mit
   sich, da kein klarer Übergabepunkt existiert.

Nach dem Decompose-Schritt (Schritt 3 in `sdd-implement`) liegt ein strukturierter
Task-Plan vor — dieser Punkt ist der natürliche Schnitt für Sub-Agenten-Delegation.
Jeder Task bekommt einen eigenen, frischen Kontext. Der Orchestrator sammelt Token-
Verbrauch und Ergebnis pro Task ein und persistiert sie in `token-history`.

Dieses Feature ist **Claude-spezifisch**: es nutzt das Claude Agent SDK zur
Sub-Agenten-Spawning. Andere Provider-Pfade bleiben unverändert (Single-Context-Mode).

## 2. Zielsetzung

**Primärziel:** Nach dem Decompose-Schritt delegiert der Hauptagent jeden Task an
einen dedizierten Sub-Agenten mit eigenem Kontext; Token-Verbrauch wird pro Task
in `token-history` gespeichert.

**Erfolgskriterien (messbar):**
- [ ] `sdd token-history SPEC-XXXX` zeigt Einträge mit `task_id`-Granularität
- [ ] `sdd calibrate SPEC-XXXX` zeigt Token-Aufschlüsselung nach Tasks
- [ ] Jeder Sub-Agent startet mit leerem Kontext (keine Cross-Task-Drift nachweisbar)
- [ ] Sub-Agenten-Fehler werden an den Orchestrator propagiert (kein Silent-Failure)
- [ ] Bei Nicht-Claude-Provider: transparenter Fallback auf Single-Context-Mode

**Nicht-Ziele (explizit):**
- Keine parallele Ausführung von Sub-Agenten (bleibt sequenziell)
- Keine Unterstützung anderer Provider als Claude (OpenAI, Gemini etc.)
- Keine Änderungen am TDD-Prozess selbst (Red → Green → Refactor bleibt unverändert)
- Kein automatisches Retry-Management auf Sub-Agenten-Ebene
- Keine Änderungen an bestehenden Contracts oder Tests anderer Specs
- Keine eigene Retry-Logik im Sub-Agenten selbst (max. 1 Retry auf Orchestrator-Ebene)

## 3. User Stories

| ID    | Als …                        | möchte ich …                                                    | um …                                                         |
|-------|------------------------------|-----------------------------------------------------------------|--------------------------------------------------------------|
| US-01 | Claude-Agent (Orchestrator)  | nach Decompose jeden Task an einen Sub-Agenten delegieren       | Kontext-Drift zu vermeiden und saubere Task-Isolation zu haben |
| US-02 | Entwickler (Boris)           | den Token-Verbrauch pro Task in `token-history` sehen           | teure Tasks zu identifizieren und Schätzungen zu verbessern  |
| US-03 | Entwickler (Boris)           | bei Sub-Agenten-Fehler einen klaren Fehlerbericht erhalten      | gezielt eingreifen zu können ohne die gesamte Session neu zu starten |

## 4. Funktionale Anforderungen

- **FR-01:** Nach `sdd decompose SPEC-XXXX` wird jeder Task aus dem Decompose-Plan
  als eigenständiger Sub-Agenten-Aufruf via Claude Agent SDK ausgeführt.
- **FR-02:** Jeder Sub-Agent erhält exakt seinen Task-Kontext: Spec, relevante
  Contracts, zugehörige Test-Stubs — kein Kontext aus anderen Tasks.
- **FR-03:** Nach Abschluss jedes Sub-Agenten werden `input_tokens`, `output_tokens`
  und `cache_read_tokens` direkt aus dem `usage`-Objekt der Agent-SDK-Response
  ausgelesen. Die Extraktion erfolgt über ein austauschbares `TokenExtractor`-Interface
  (Strategy Pattern), sodass die Implementierung bei gewonnener Erfahrung angepasst
  werden kann ohne FR-03 zu brechen.
- **FR-04:** Token-Verbrauch pro Task wird in `token-history` mit `task_id` und
  `task_label` gespeichert (Erweiterung des bestehenden Schemas aus SPEC-0011).
- **FR-05:** `sdd calibrate SPEC-XXXX` zeigt neben dem Gesamt-Verbrauch eine
  Aufschlüsselung nach Tasks an (sofern task-granulare Einträge vorhanden).
- **FR-06:** Schlägt ein Sub-Agent fehl, erhält er exakt 1 Retry. Schlägt auch der
  Retry fehl, propagiert der Orchestrator den Fehler, hält an und gibt einen
  Fehlerbericht aus — kein Silent-Failure.
- **FR-07:** Jeder Sub-Agent erhält nur die CON-IDs die im Task-Label referenziert
  sind (nicht alle Contracts der Spec). Voraussetzung: `sdd decompose` gibt
  strukturierte Task-Labels mit CON-Referenzen aus.
- **FR-08:** Die Sub-Agenten-Delegation wird durch den CLI-Befehl `sdd implement`
  gesteuert (nicht durch den Skill direkt). Der Skill ruft `sdd implement SPEC-XXXX`
  auf; Provider-Guard, Sub-Agenten-Spawning und Token-Persistierung liegen im
  Python-Code.
- **FR-09:** Ist der aktive Provider nicht Claude, wird die Sub-Agenten-Delegation
  übersprungen und der bisherige Single-Context-Mode ausgeführt (Fallback transparent
  im Output gekennzeichnet).

## 5. Nicht-funktionale Anforderungen

| Kategorie    | Anforderung                                                                 |
|--------------|-----------------------------------------------------------------------------|
| Performance  | Kein messbarer Overhead durch Sub-Agenten-Spawning (< 2s Latenz pro Task)  |
| Observability| Token-Verbrauch pro Task wird strukturiert geloggt (audit.log + token-history) |
| Portabilität | Fallback auf Single-Context-Mode wenn Provider ≠ Claude                    |
| Korrektheit  | Summe der Sub-Agenten-Token entspricht dem tatsächlichen Gesamtverbrauch    |

## 6. Akzeptanzkriterien (Gherkin)

```gherkin
Feature: Sub-Agenten-Delegation in sdd-implement

  Scenario: Erfolgreiche Delegation mit Token-Tracking
    Given eine Spec SPEC-XXXX mit 4 Decompose-Tasks
    And der aktive Provider ist Claude
    When sdd-implement SPEC-XXXX ausgeführt wird
    Then werden 4 Sub-Agenten sequenziell gespawnt
    And jeder Sub-Agent startet mit leerem Kontext
    And token-history enthält 4 Einträge mit task_id für SPEC-XXXX

  Scenario: Sub-Agenten-Fehler mit Retry und Eskalation
    Given eine Spec SPEC-XXXX mit 3 Tasks
    And Task 2 schlägt fehl (TDD-Loop ohne Fortschritt)
    When sdd-implement SPEC-XXXX ausgeführt wird
    Then wird Task 2 einmal wiederholt
    And schlägt der Retry ebenfalls fehl
    Then hält der Orchestrator an und gibt einen Fehlerbericht für Task 2 aus
    And Task 3 wird nicht gestartet

  Scenario: Fallback bei Nicht-Claude-Provider
    Given eine Spec SPEC-XXXX
    And der aktive Provider ist nicht Claude
    When sdd-implement SPEC-XXXX ausgeführt wird
    Then läuft die Implementierung im Single-Context-Mode
    And der Output kennzeichnet "[Fallback: Single-Context-Mode]"
```

## 7. Architektur & Design Patterns

### Mediator Pattern
> [Refactoring Guru – Mediator](https://refactoring.guru/design-patterns/mediator)

Der Hauptagent (Orchestrator) agiert als Mediator: Er koordiniert die Kommunikation
zwischen Decompose-Output und den Sub-Agenten, ohne dass Sub-Agenten voneinander
wissen. Jeder Sub-Agent kennt nur seinen eigenen Task-Kontext.

**Begründung:** Vermeidet direkte Kopplung zwischen Tasks. Der Orchestrator ist der
einzige Punkt der den Gesamtzustand (welche Tasks erledigt sind, kumulierte Tokens)
hält.

### Decorator Pattern
> [Refactoring Guru – Decorator](https://refactoring.guru/design-patterns/decorator)

Jeder Sub-Agenten-Aufruf wird mit einem Token-Tracking-Decorator umhüllt: Vor dem
Aufruf wird ein Timer/Context geöffnet, nach dem Aufruf werden Token-Daten aus der
Agent-SDK-Response extrahiert und persistiert.

**Begründung:** Token-Tracking ist eine Querschnittsaufgabe — sie soll nicht in die
Task-Logik des Sub-Agenten eingebettet werden. Der Decorator hält die Verantwortung
sauber getrennt.

### Datenfluss

```
sdd implement SPEC-XXXX          ← CLI-Befehl (neu)
    │
    ├── Provider-Check: Claude? → sonst Single-Context-Fallback
    │
    ├── sdd decompose SPEC-XXXX  →  [Task{id, label, con_ids[]}, ...]
    │
    └── für jeden Task:
            │
            ├── Contracts filtern: nur task.con_ids (nicht alle Spec-Contracts)
            ├── [Decorator: Token-Context öffnen]
            ├── Sub-Agent spawnen (Claude Agent SDK)
            │       └── Kontext: Spec + gefilterte Contracts + Task-Test-Stubs
            │       └── TDD-Zyklus ausführen
            │       └── Ergebnis + usage{input, output, cache_read} zurückgeben
            ├── [Decorator: TokenExtractor.extract(usage) → TokenRecord]
            ├── token-history persistieren (spec_id, task_id, task_label, tokens)
            └── bei Fehler: 1 Retry → bei erneutem Fehler: Orchestrator hält an
```

## 8. Contracts (was wird garantiert)

| Contract-ID | Typ      | Was wird garantiert?                                                       |
|-------------|----------|----------------------------------------------------------------------------|
| CON-XXXX    | data     | Token-History-Schema-Erweiterung: `task_id`, `task_label` als optionale Felder |
| CON-XXXX    | behavior | Sub-Agenten-Delegation-Protokoll: Kontext-Übergabe, Token-Reporting, Fehler-Propagation |

## 9. Tests (wie wird verifiziert)

| Test-ID  | Level    | Was prüft der Test?                                                     |
|----------|----------|-------------------------------------------------------------------------|
| TST-XXXX | unit     | Token-Aggregation: Summe Sub-Agenten-Token == Gesamt-Eintrag in token-history |
| TST-XXXX | unit     | Fallback-Logik: Single-Context-Mode bei Nicht-Claude-Provider           |
| TST-XXXX | contract | Token-History-Schema: task_id-Felder werden korrekt geschrieben/gelesen |
| TST-XXXX | contract | Fehler-Propagation: Sub-Agenten-Fehler hält Orchestrator an             |

## 10. Implementierungsreihenfolge

1. `sdd decompose` um strukturierte Task-Labels mit CON-Referenzen erweitern
2. Token-History-Schema in `estimation.py` um `task_id` / `task_label` erweitern (SPEC-0011-Erweiterung)
3. `TokenExtractor`-Interface + Agent-SDK-Implementierung anlegen
4. `calibrate`-Command: per-Task-Aufschlüsselung im Output ergänzen
5. Neuen CLI-Befehl `sdd implement` anlegen (Provider-Guard, Sub-Agenten-Loop, Retry, Token-Persistierung)
6. `sdd-implement`-Skill: Schritt 3 auf `sdd implement SPEC-XXXX` umstellen
7. Fallback-Logik für Nicht-Claude-Provider (Single-Context-Mode)
8. Contracts und Tests anlegen

## 11. Offene Fragen

- [x] Token-Verbrauch: direkt via `usage`-Objekt der Agent-SDK-Response; austauschbar via `TokenExtractor`-Interface
- [x] Retry: 1 Retry bei Scheitern, dann Eskalation an Orchestrator
- [x] Contract-Filter: nur task-referenzierte CON-IDs (`sdd decompose` muss CON-IDs in Task-Labels liefern)
- [x] Ownership: CLI-Befehl `sdd implement` (nicht Skill); Skill ruft `sdd implement` auf

## 12. Änderungshistorie

| Datum      | Version | Autor      | Änderung            |
|------------|---------|------------|---------------------|
| 2026-06-02 | 0.1.0   | borisbrue  | Initiale Erstellung |
