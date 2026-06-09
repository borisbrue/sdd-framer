---
id: SPEC-0042
title: Holdout-Runner Tiered Loop & Smoke Test
type: feature
status: in-progress
owner: Boris
created: 2026-06-09
updated: '2026-06-09'
version: 0.1.0
priority: high
tags:
- holdout
- evaluate
- sdd-implement
- loop
depends_on:
- SPEC-0004
contracts:
- CON-0161
- CON-0162
- CON-0163
- CON-0164
tests:
- TST-0188
- TST-0189
- TST-0190
- TST-0191
- TST-0192
fr_test_map:
  FR-01:
  - TST-0189
  FR-02:
  - TST-0190
  FR-03:
  - TST-0190
  FR-04:
  - TST-0188
  - TST-0191
  FR-05:
  - TST-0188
  FR-06:
  - TST-0191
adrs: []
started_at: '2026-06-09T15:15:46Z'
---
# Holdout-Runner Tiered Loop & Smoke Test

> **Status:** draft · **Owner:** Boris · **Version:** 0.1.0

## 1. Kontext & Motivation

Der Holdout-Runner (`holdout_runner.py`) führt Holdouts bereits in drei Prioritäts-Stufen aus
(critical → normal → edge-case) mit Fail-Fast-Semantik. Dieses Verhalten ist jedoch in der
Implementierungsschleife (`sdd-implement.md` Schritt 5.5) nicht sichtbar: der Skill ruft
`sdd evaluate` einmal auf und geht bei jedem Fehler pauschal zurück zu Schritt 4 — unabhängig
davon, welche Tier failed.

Das führt dazu, dass:
- Ein critical-Fehler (der einen Container-Neustart erfordert) identisch behandelt wird wie ein
  edge-case-Fehler (der ein Task-Delta braucht)
- Der Agent den `task_delta` aus dem Evaluation-Report nicht explizit nutzt
- Es kein automatisiertes End-to-End-Smoke-Test gibt, das den vollständigen Loop verifiziert

**Stakeholder:** Boris (Blueprint-Nutzer), jeder KI-Agent der `/sdd-implement` ausführt.

## 2. Zielsetzung

**Primärziel:**
Der sdd-implement-Loop reagiert tier-spezifisch auf Holdout-Fehler — critical-Fehler starten
den Container neu (Schritt 1), normal/edge-case-Fehler patchen Tasks und re-evaluieren.

**Erfolgskriterien (messbar):**
- [ ] `sdd evaluate --tier critical` gibt nur critical-Holdouts aus und hat korrekten Exit-Code
- [ ] `sdd evaluate --tier normal` und `--tier edge-case` analog
- [ ] sdd-implement Schritt 5.5 liest den Report und verzweigt tier-spezifisch
- [ ] Ein automatisierter Smoke-Test verifiziert alle drei Tier-Kombinationen in < 5 s (ohne Container)

**Nicht-Ziele:**
- Keine Änderung an der Kern-Logik des Runners (PRIORITY_ORDER, fail-fast — bereits korrekt)
- Kein neues Bewertungsmodell (LLM-Provider bleibt optional)
- Kein grafisches Dashboard

## 3. User Stories

| ID    | Als ...           | möchte ich ...                                                      | um ...                                          |
|-------|-------------------|---------------------------------------------------------------------|-------------------------------------------------|
| US-01 | KI-Agent          | bei critical-Holdout-Fehler einen Hinweis auf Schritt 1 erhalten   | den Container neu zu starten statt nur Code zu patchen |
| US-02 | KI-Agent          | den generierten `task_delta` aus dem Report direkt lesen            | 1–2 Tasks gezielt zu patchen ohne Re-Analyse    |
| US-03 | Boris             | `sdd evaluate --tier critical` ausführen                            | schnelles Feedback im CI ohne die Edge-Cases    |
| US-04 | Boris             | einen Smoke-Test-Befehl für den Runner                              | den Loop nach Änderungen automatisch zu verifizieren |

## 4. Funktionale Anforderungen

- **FR-01:** `sdd evaluate` akzeptiert ein optionales `--tier critical|normal|edge-case` Flag.
  Wenn gesetzt, werden nur Holdouts dieser Priorität ausgeführt (keine Fail-Fast-Übersprünge).
- **FR-02:** Der Evaluation-Report enthält pro Szenario das `priority`-Feld im JSON-Output.
- **FR-03:** `sdd evaluate` gibt bei `--output-json` einen `tier_summary`-Block aus:
  `{"critical": {"passed": N, "failed": M}, "normal": {...}, "edge-case": {...}}`.
- **FR-04:** sdd-implement.md Schritt 5.5 liest den `tier_summary` aus dem Report und
  verzweigt:
  - critical-Fehler → Container neu starten (zurück zu Schritt 1b), dann nur critical re-evaluieren
  - normal-Fehler → `task_delta` aus Report lesen, Tasks patchen, alle Tiers re-evaluieren
  - edge-case-Fehler → `task_delta` lesen, Tasks patchen, alle Tiers re-evaluieren
- **FR-05:** Das `task_delta`-Feld im JSON-Output des Reports wird explizit als
  "Patch-Anweisung für den Agenten" dokumentiert (im Skill-Prompt sichtbar).
- **FR-06:** Ein neues `sdd evaluate --smoke` Flag führt einen deterministischen Selbsttest
  durch: Es prüft ob der Runner mit Mock-Holdouts (ohne Container) korrekt sortiert,
  fail-fast anwendet und Exit-Codes setzt. Läuft in < 2 s.

## 5. Nicht-funktionale Anforderungen

| Kategorie    | Anforderung                                                              |
|--------------|--------------------------------------------------------------------------|
| Performance  | `sdd evaluate --tier critical` darf nicht langsamer sein als volles evaluate |
| Testbarkeit  | FR-06 Smoke-Test läuft ohne Container, ohne LLM-Provider (rein lokal)   |
| Rückwärtskompatibilität | Bestehende `sdd evaluate`-Aufrufe ohne `--tier` bleiben unverändert |
| Skill-Kohärenz | sdd-implement.md muss konsistent mit dem Diagramm in Abschnitt 8 sein |

## 6. Akzeptanzkriterien (Gherkin)

```gherkin
Feature: Tiered Holdout-Evaluation

  Scenario: Critical-Fehler überspringt nachgelagerte Tiers
    Given drei Holdouts: HOL-A (critical, fail), HOL-B (normal), HOL-C (edge-case)
    When "sdd evaluate --spec SPEC-XXXX" ausgeführt wird
    Then HOL-A schlägt fehl
    And HOL-B und HOL-C haben Status "skipped"
    And Exit-Code ist 1
    And tier_summary zeigt critical.failed=1, normal.skipped=1, edge-case.skipped=1

  Scenario: Tier-Filter läuft nur die gewählte Priorität
    Given dieselben drei Holdouts
    When "sdd evaluate --spec SPEC-XXXX --tier normal" ausgeführt wird
    Then nur HOL-B wird ausgeführt
    And HOL-A und HOL-C werden nicht angerührt
    And Exit-Code ist 0 (HOL-B pass) oder 1 (HOL-B fail)

  Scenario: Alle Tiers bestehen
    Given drei Holdouts: HOL-A (critical, pass), HOL-B (normal, pass), HOL-C (edge-case, pass)
    When "sdd evaluate --spec SPEC-XXXX" ausgeführt wird
    Then alle drei haben Status "passed"
    And Exit-Code ist 0

  Scenario: Smoke-Test ohne Container
    When "sdd evaluate --smoke" ausgeführt wird
    Then kein HTTP-Aufruf wird gemacht
    And Ausgabe zeigt "✓ Tier-Sortierung korrekt"
    And Ausgabe zeigt "✓ Fail-Fast critical→normal korrekt"
    And Ausgabe zeigt "✓ Fail-Fast normal→edge-case korrekt"
    And Exit-Code ist 0
    And Laufzeit < 2 s
```

## 7. Edge Cases & Fehlerfälle

- `--tier` und `--hol-ids` kombiniert: `--hol-ids` hat Vorrang, `--tier` wird ignoriert (Warning ausgeben)
- Keine Holdouts für den gewählten `--tier`: Exit 0, Meldung "0 Holdouts für tier=X gefunden"
- `--smoke` mit `--spec` oder `--base-url`: `--smoke` hat Vorrang, andere Flags werden ignoriert
- Provider nicht verfügbar: `task_delta` bleibt leer, kein Fehler (bereits so implementiert)

## 8. Contracts (was wird garantiert)

Der Loop — wie er nach Implementierung dieser Spec in sdd-implement.md stehen soll:

```
sdd implement (Tasks ausführen)
       ↓
Schritt 1b: docker build → Container starten
       ↓
Schritt 5.5a: nur critical Holdouts laufen (--tier critical)
       ↓ fail                              ↓ pass
Agent liest: task_delta aus Report        Schritt 5.5b: normal Holdouts (--tier normal)
Agent patcht 1–2 Tasks                         ↓ fail              ↓ pass
→ zurück zu Schritt 1b                   Agent liest            Schritt 5.5c: edge-case
  (Container neu)                        task_delta aus Report        ↓ fail      ↓ pass
                                         Tasks patchen          Agent liest    ✓ Schritt 6
                                         → re-evaluate alle     task_delta
                                                                Tasks patchen
                                                                → re-evaluate alle
```

Diese Spec wird durch folgende Contracts maschinell prüfbar gemacht:

| Contract-ID | Typ        | Was wird garantiert?                                          |
|-------------|------------|---------------------------------------------------------------|
| CON-XXXX    | api        | `sdd evaluate --tier` CLI-Interface (Flags, Exit-Codes)       |
| CON-XXXX    | data       | JSON-Output Schema mit `tier_summary` und `task_delta`        |
| CON-XXXX    | behavior   | Fail-Fast- und Tier-Filter-Semantik (Gherkin)                 |
| CON-XXXX    | behavior   | sdd-implement Schritt 5.5 tier-spezifisches Verzweigungsverhalten |

## 9. Tests (wie wird verifiziert)

| Test-ID  | Level      | Was prüft der Test?                                          |
|----------|------------|--------------------------------------------------------------|
| TST-XXXX | unit       | `run_structured_holdouts` mit Mock-Holdouts: Tier-Sortierung, Fail-Fast |
| TST-XXXX | contract   | `sdd evaluate --tier X` Flags und Exit-Codes (CLI-Level)     |
| TST-XXXX | contract   | JSON-Output `tier_summary`-Schema                            |
| TST-XXXX | acceptance | `sdd evaluate --smoke` Selbsttest-Szenarien                  |

## 10. Offene Fragen

- [ ] Soll `--tier` mehrfach angegeben werden können? (`--tier critical --tier normal`)
- [ ] Soll der Skill explizit in Schritt 5.5 `--output-json` nutzen um den Report zu parsen?

## 11. Änderungshistorie

| Datum      | Version | Autor  | Änderung                          |
|------------|---------|--------|-----------------------------------|
| 2026-06-09 | 0.1.0   | Boris  | Initiale Erstellung (rekonstruiert) |
