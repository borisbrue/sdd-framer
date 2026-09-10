---
id: SPEC-0014
title: "Staged SPEC Execution Gate – Geführter Qualitätsprozess mit Contract-Konflikt-Analyse"
status: implemented
owner: Boris
created: 2026-05-14
updated: 2026-05-14
approved: 2026-05-14
version: 0.1.0
priority: high
tags:
  - execution-gate
  - quality-gate
  - conflict-detection
  - staged-workflow
  - contract-analysis
  - test-generation
depends_on:
  - SPEC-0005
  - SPEC-0010
contracts:
  - CON-0025
  - CON-0026
  - CON-0027
  - CON-0028
  - CON-0029
  - CON-0030
tests:
  - TST-0037
  - TST-0038
  - TST-0039
  - TST-0040
  - TST-0041
  - TST-0042
adrs: []
---

# Staged SPEC Execution Gate – Geführter Qualitätsprozess mit Contract-Konflikt-Analyse

> **Status:** draft · **Owner:** Boris · **Version:** 0.1.0

## 1. Kontext & Motivation

Im aktuellen SDD-System kann `sdd execute` auf jede SPEC mit Status `approved` angewendet
werden — unabhängig davon, ob die Contracts vollständig sind, Tests existieren oder die
Contracts mit anderen Contracts des Projekts in Konflikt stehen.

Das führt zu drei konkreten, kostspieligen Problemen:

1. **Blinde Execution:** Eine SPEC wird ausgeführt, obwohl unklar ist, welche Tests
   geschrieben werden müssen. Bugs werden erst im Evaluator-Lauf sichtbar.
2. **Contract-Kollisionen:** Ein neuer Contract überschneidet sich mit einem bestehenden
   (z. B. zwei Contracts definieren denselben API-Endpunkt oder dasselbe Datenfeld
   unterschiedlich). Die Kollision öffnet weitere Baustellen, die nicht eingeplant wurden.
3. **Fehlende Impact-Transparenz:** Vor der Execution ist nicht klar, welche anderen SPECs,
   Contracts und Tests von einer Änderung betroffen sind.

Diese SPEC definiert einen **verpflichtenden, gestuften Qualitätsprozess** (Execution Gate),
der `sdd execute` blockiert, bis alle Phasen erfolgreich abgeschlossen sind. Jede Phase hat
definierte Eintritts- und Exitkriterien. Die Contract-Konflikt-Analyse prüft neue Contracts
gegen **alle aktiven Contracts im Workspace** und erzeugt einen Konfliktbericht mit
Impact-Abschätzung, bevor eine Execution freigegeben werden kann.

## 2. Zielsetzung

**Primärziel:**
`sdd execute` ist erst möglich, wenn der vollständige Qualitätsprozess durchlaufen wurde:
SPEC-Inhalt geprüft, Contracts geschrieben, gegen den Workspace geprüft, Tests generiert
und eine Regression-Prüfung bestanden.

**Erfolgskriterien (messbar):**
- [ ] `sdd execute` gibt Fehlercode 2 zurück und gibt eine Phasen-Statusübersicht aus,
  solange nicht alle Gates grün sind
- [ ] Contract-Konflikt-Analyse läuft in < 30 s für einen Workspace mit 50 Contracts
- [ ] Ein Konfliktbericht nennt für jeden Konflikt: betroffene Contract-IDs, Art des Konflikts,
  betroffene SPECs und eine Risikobewertung (low / medium / high)
- [ ] Auto-generierte Tests sind syntaktisch valid (pytest läuft durch) und decken mindestens
  alle Scenarios im Gherkin-Contract ab
- [ ] Der Phasenstatus ist persistent im Pipeline-JSON gespeichert und über die Web UI einsehbar
- [ ] Jede Phase kann einzeln erneut ausgeführt werden ohne vorherige Phasen neu zu starten
- [ ] Phasenergebnis-Feedback des LLM ist in < 10 s sichtbar

**Nicht-Ziele (explizit):**
- Automatisches Beheben von Contract-Konflikten (Konflikt wird gemeldet, Lösung liegt beim Autor)
- Vollautomatische SPEC-Genehmigung ohne menschliche Freigabe im Default-Betrieb.
  Ausnahme: SPEC-0037 (Autopilot-Modus) darf Gates automatisch passieren, wenn
  `autopilot.automated_gate_approval: true` in `.sdd/config.yaml` explizit gesetzt
  ist und alle Exit-Kriterien des Gates erfüllt sind — das ist kein Bypass, sondern
  ein konfiguriertes Opt-in mit denselben Exit-Kriterien wie die manuelle Freigabe.
- Prüfung von Contracts über Workspace-Grenzen hinweg (nur aktueller Workspace)
- Integration in den VS Code Extension-Execute-Flow (Folgespec)
- Rückwirkende Prüfung bereits implementierter SPECs

## 3. Der gesteuerte Phasenprozess

### 3.1 Überblick der Phasen

```
Phase 1: SPEC-Draft         ← Autor schreibt SPEC
    ↓  [sdd spec review]
Phase 2: SPEC-Review        ← LLM analysiert Vollständigkeit, Messbarkeit, Ambiguität
    ↓  [manuell: Author bestätigt / verbessert]
Phase 3: Contracts-Proposed ← LLM schlägt benötigte Contracts vor (Typ, Format, Scope)
    ↓  [sdd contract write]
Phase 4: Contracts-Draft    ← Autor schreibt Contracts
    ↓  [sdd contract review]
Phase 5: Contracts-Review   ← LLM verbessert + Konflikt-Analyse gegen Workspace
    ↓  [manuell: Autor löst Konflikte / bestätigt Impact]
Phase 6: Tests-Generated    ← Tests werden automatisch aus Contracts generiert
    ↓  [sdd test run --regression]
Phase 7: Regression-OK      ← Generierte Tests laufen durch (kein Fehler in bestehenden Tests)
    ↓  [sdd spec approve]
Phase 8: SPEC-Approved      ← Finale LLM-Prüfung: SPEC konsistent mit finalen Contracts?
    ↓
Phase 9: Execute-Unlocked   ← sdd execute ist freigegeben
```

### 3.2 Phasenübergänge und Exit-Kriterien

| Phase | Exit-Kriterium | Auslöser |
|-------|---------------|----------|
| 1 → 2 | SPEC hat Pflichtfelder (id, title, status, owner) | `sdd spec review <id>` |
| 2 → 3 | LLM-Review hat 0 offene Critique-Items oder Autor hat alle explizit dismissed | `sdd contract propose <id>` |
| 3 → 4 | Mindestens ein Contract-Vorschlag existiert | Manuell nach Review |
| 4 → 5 | Alle vorgeschlagenen Contracts sind als Dateien angelegt | `sdd contract review <id>` |
| 5 → 6 | Konflikt-Analyse abgeschlossen + alle Konflikte als "acknowledged" oder "resolved" markiert | `sdd test generate <id>` |
| 6 → 7 | Testdateien syntaktisch valide, pytest dry-run erfolgreich | `sdd test run --regression <id>` |
| 7 → 8 | Alle Test-Runs grün (pass_threshold erfüllt) | `sdd spec approve <id>` |
| 8 → 9 | LLM-Konsistenzcheck: SPEC ↔ Contracts widerspruchsfrei | Automatisch nach Phase 8 |

### 3.3 Persistenz des Phasenstatus

Der Phasenstatus wird in das bestehende Pipeline-JSON-Format (`/.sdd/pipeline/`) geschrieben:

```json
{
  "spec_id": "SPEC-0014",
  "pipeline_phase": "contracts-review",
  "phase_history": [
    { "phase": "spec-draft",          "completed_at": "...", "result": "ok" },
    { "phase": "spec-review",         "completed_at": "...", "result": "ok", "dismissed_items": 2 },
    { "phase": "contracts-proposed",  "completed_at": "...", "result": "ok", "proposed": ["CON-X", "CON-Y"] }
  ],
  "blocking_issues": [],
  "conflict_report_ref": ".sdd/conflict-reports/SPEC-0014-conflicts.json"
}
```

## 4. Contract-Konflikt-Analyse

### 4.1 Was als Konflikt gilt

Ein **Konflikt** liegt vor, wenn ein neuer oder geänderter Contract mit einem bestehenden
aktiven Contract im Workspace semantisch überlappt:

| Konflikt-Typ | Beschreibung | Beispiel |
|---|---|---|
| `endpoint-overlap` | Zwei API-Contracts definieren denselben HTTP-Endpunkt | `POST /v1/analyze` in CON-0014 und einem neuen Contract |
| `field-contradiction` | Zwei Data-Contracts definieren dasselbe Feld mit inkompatiblen Typen/Constraints | `user.id` als `string` vs. `integer` |
| `behavior-contradiction` | Zwei Behavior-Contracts definieren dasselbe Szenario mit unterschiedlichem Ergebnis | Login-Fehler → HTTP 401 vs. HTTP 403 |
| `scope-overlap` | Zwei Contracts adressieren denselben fachlichen Bereich ohne klare Abgrenzung | Zwei Contracts für "Token-Verwaltung" |
| `dependency-gap` | Contract referenziert eine externe Schnittstelle, die kein eigener Contract abdeckt | gRPC-Call ohne eigenen gRPC-Contract |

### 4.2 Konflikt-Analyse-Prozess

```
Neuer Contract (CON-NEW)
        |
        ▼
1. Strukturelle Extraktion
   - Endpunkte, Felder, Szenarien, Scope-Keywords aus CON-NEW extrahieren
        |
        ▼
2. Workspace-Scan
   - Alle aktiven Contracts des Projekts laden (status: active | draft)
   - Strukturelle Extraktion für jeden Contract (gecacht)
        |
        ▼
3. LLM-Konflikt-Prüfung
   - Prompt: "Gegeben CON-NEW und folgende bestehende Contracts, identifiziere Überschneidungen..."
   - Output: strukturierter JSON-Konfliktbericht
        |
        ▼
4. Impact-Analyse
   - Für jeden identifizierten Konflikt: welche SPECs referenzieren den betroffenen Contract?
   - Impact-Score = Anzahl betroffener SPECs × Konflikt-Schweregrad
        |
        ▼
5. Konfliktbericht ausgeben
   - Datei: .sdd/conflict-reports/SPEC-XXXX-conflicts.json
   - CLI-Output: Tabelle aller Konflikte mit IDs, Typ, Schwere, Impact
```

### 4.3 Konfliktbericht-Format

```json
{
  "spec_id": "SPEC-0014",
  "generated_at": "2026-05-14T12:00:00Z",
  "new_contracts": ["CON-0025"],
  "conflicts": [
    {
      "id": "CF-001",
      "type": "endpoint-overlap",
      "severity": "high",
      "new_contract": "CON-0025",
      "conflicting_contract": "CON-0014",
      "detail": "POST /v1/analyze ist bereits in CON-0014 definiert. CON-0025 erweitert denselben Endpunkt ohne Versionierung.",
      "affected_specs": ["SPEC-0005"],
      "required_action": "Endpunkt versionieren (v2) oder Contract CON-0014 erweitern",
      "status": "open"
    }
  ],
  "impact_summary": {
    "total_conflicts": 1,
    "high": 1,
    "medium": 0,
    "low": 0,
    "affected_specs_count": 1
  }
}
```

### 4.4 Konflikt-Auflösung (Pflicht vor Phase 6)

Für jeden offenen Konflikt muss der Autor eine der folgenden Aktionen durchführen:

- `sdd conflict resolve <CF-ID> --action <refactor|extend|version|split>` — Lösung dokumentieren
- `sdd conflict acknowledge <CF-ID> --reason "<Begründung>"` — bewusste Entscheidung, Konflikt zu akzeptieren

Erst wenn alle Konflikte `status: resolved | acknowledged` haben, ist Phase 6 erreichbar.

## 5. Automatische Test-Generierung (Phase 6)

### 5.1 Generierungsstrategie pro Contract-Typ

| Contract-Format | Generierungsstrategie | Output |
|---|---|---|
| Gherkin (`.feature`) | Feature-Szenarien → pytest-bdd Scenarios | `tests/behavior/test_<con-id>.py` |
| OpenAPI (`.yaml`) | Endpunkte + Examples → pytest + httpx | `tests/api/test_<con-id>.py` |
| JSON Schema | Schema-Constraints → pytest + jsonschema | `tests/data/test_<con-id>.py` |
| SLO-YAML | SLO-Thresholds → Performance-Assertions | `tests/performance/test_<con-id>.py` |

### 5.2 Qualitätskriterien für generierte Tests

- Jedes Gherkin-Scenario hat mindestens einen generierten Test-Case
- Happy-Path und definierte Error-Cases sind beide abgedeckt
- Tests sind eigenständig lauffähig (kein globaler State)
- Testdatei enthält im Header: `# AUTO-GENERATED from <CON-ID> via sdd test generate`
- Generierte Tests dürfen nach Erstellung manuell ergänzt, aber nicht gelöscht werden

## 6. Execute-Gate Enforcement

### 6.1 CLI-Verhalten bei blockierter SPEC

```bash
$ sdd execute SPEC-0014

ERROR: SPEC-0014 kann nicht ausgeführt werden – Execution Gate nicht bestanden.

Phasen-Status:
  ✓ Phase 1 – SPEC-Draft           abgeschlossen
  ✓ Phase 2 – SPEC-Review          abgeschlossen (2 Items dismissed)
  ✓ Phase 3 – Contracts-Proposed   abgeschlossen (CON-0025, CON-0026 vorgeschlagen)
  ✓ Phase 4 – Contracts-Draft      abgeschlossen
  ✗ Phase 5 – Contracts-Review     BLOCKIERT
    → 1 offener Konflikt: CF-001 (high, endpoint-overlap mit CON-0014)
    → Aktion erforderlich: sdd conflict resolve CF-001

Weitere Phasen: nicht auswertbar bis Phase 5 bestanden.
Exit code: 2
```

### 6.2 Override-Mechanismus (explizit, nicht stillschweigend)

Ein manueller Override ist möglich, aber explizit sichtbar:

```bash
sdd execute SPEC-0014 --force --override-reason "Hotfix: CF-001 wird in SPEC-0015 adressiert"
```

Der Override wird im Pipeline-JSON protokolliert und ist in der Web UI als Warnung sichtbar.
`--force` ohne `--override-reason` wird abgelehnt.

## 7. User Stories

| ID    | Als ...       | möchte ich ...                                                    | um ...                                            |
|-------|---------------|-------------------------------------------------------------------|--------------------------------------------------|
| US-01 | SPEC-Autor    | eine klare Übersicht, welche Phasen noch offen sind              | zu wissen, was ich als Nächstes tun muss         |
| US-02 | SPEC-Autor    | einen Konfliktbericht vor der Execution sehen                    | unerwartete Baustellen zu vermeiden               |
| US-03 | SPEC-Autor    | automatisch generierte Tests als Ausgangspunkt haben             | keine Test-Vorlage von Hand schreiben zu müssen   |
| US-04 | Tech Lead     | einen Override mit Begründung dokumentieren können               | in Ausnahmefällen nicht vom Prozess blockiert zu werden |
| US-05 | Tech Lead     | im Pipeline-Bericht sehen, ob SPECs per Override freigegeben wurden | Qualitätsrisiken nachverfolgen zu können       |
| US-06 | SPEC-Autor    | dass Phase 6 bei einer bereits gecachten Workspace-Analyse schnell läuft | nicht bei jedem Contract-Commit 30 s zu warten |

## 8. Funktionale Anforderungen

- **FR-01:** `sdd execute <SPEC-ID>` prüft den Phasenstatus vor der Ausführung und bricht mit
  Exit-Code 2 ab, wenn nicht alle Phasen grün sind.
- **FR-02:** `sdd spec review <SPEC-ID>` führt eine LLM-basierte Inhaltsprüfung durch und
  gibt strukturiertes Feedback (Critique-Items mit Abschnittsbezug).
- **FR-03:** `sdd contract propose <SPEC-ID>` schlägt auf Basis des SPEC-Inhalts eine Liste
  von Contracts (ID-Vorschlag, Typ, Format, Kurzbeschreibung) vor.
- **FR-04:** `sdd contract review <SPEC-ID>` führt die Contract-Konflikt-Analyse durch und
  schreibt den Konfliktbericht nach `.sdd/conflict-reports/`.
- **FR-05:** `sdd test generate <SPEC-ID>` generiert Testdateien aus allen Contracts der SPEC.
- **FR-06:** `sdd conflict list <SPEC-ID>` zeigt alle offenen/resolved/acknowledged Konflikte.
- **FR-07:** `sdd conflict resolve` und `sdd conflict acknowledge` aktualisieren den
  Konfliktstatus im Pipeline-JSON.
- **FR-08:** `sdd spec approve <SPEC-ID>` führt einen finalen LLM-Konsistenzcheck
  (SPEC ↔ Contracts) durch und setzt Phase 8 auf grün, wenn widerspruchsfrei.
- **FR-09:** Der Phasenstatus ist über die Web UI (SPEC-Detailseite) als Timeline einsehbar.
- **FR-10:** Workspace-Contract-Extraktion wird gecacht (Invalidierung bei Contract-Änderung).
- **FR-11:** `sdd execute <SPEC-ID> --force --override-reason "<text>"` ermöglicht expliziten
  Override; der Override wird im Pipeline-JSON mit Zeitstempel und Begründung protokolliert.

## 9. Nicht-funktionale Anforderungen

| Kategorie     | Anforderung                                                                      |
|---------------|----------------------------------------------------------------------------------|
| Performance   | Contract-Konflikt-Analyse < 30 s bei 50 Contracts im Workspace                  |
| Performance   | LLM-Feedback (spec review, contract review) in < 10 s sichtbar (Streaming)      |
| Zuverlässigkeit | Phasenstatus überlebt CLI-Crashes (persistiert nach jedem Phasenabschluss)     |
| Erweiterbarkeit | Neue Konflikt-Typen können als Plugin-Checker registriert werden               |
| Observability | Jeder Phasenübergang erzeugt einen Eintrag im strukturierten Log                |
| Sicherheit    | `--force`-Override ohne `--override-reason` wird hart abgelehnt (kein silent skip) |

## 10. Akzeptanzkriterien (Gherkin)

```gherkin
Feature: Staged SPEC Execution Gate

  Scenario: Execute blockiert wenn Phasen unvollständig
    Given SPEC-0014 hat pipeline_phase "contracts-review"
    And Konflikt CF-001 hat status "open"
    When "sdd execute SPEC-0014" ausgeführt wird
    Then ist der Exit-Code 2
    And der Output enthält "Execution Gate nicht bestanden"
    And der Output enthält "CF-001"

  Scenario: Contract-Konflikt-Analyse erkennt Endpunkt-Überschneidung
    Given CON-0025 definiert "POST /v1/analyze"
    And CON-0014 definiert ebenfalls "POST /v1/analyze"
    When "sdd contract review SPEC-0014" ausgeführt wird
    Then enthält der Konfliktbericht einen Konflikt vom Typ "endpoint-overlap"
    And der Konflikt referenziert CON-0014 als conflicting_contract
    And severity ist "high"

  Scenario: Alle Phasen grün – Execute freigegeben
    Given alle 8 Phasen von SPEC-0014 haben status "ok"
    And keine Konflikte haben status "open"
    When "sdd execute SPEC-0014" ausgeführt wird
    Then wird die Execution gestartet (Exit-Code 0)

  Scenario: Override mit Begründung wird akzeptiert und protokolliert
    Given Phase 5 von SPEC-0014 ist noch offen
    When "sdd execute SPEC-0014 --force --override-reason 'Hotfix'" ausgeführt wird
    Then wird die Execution gestartet
    And das Pipeline-JSON enthält ein "override"-Eintrag mit reason und timestamp

  Scenario: Auto-generierte Tests decken Gherkin-Scenarios ab
    Given CON-0025 enthält 3 Gherkin-Scenarios
    When "sdd test generate SPEC-0014" ausgeführt wird
    Then existiert "tests/contract/test_con_0025.py"
    And die Datei enthält mindestens 3 Test-Funktionen
    And pytest --collect-only läuft ohne Fehler durch

  Scenario: Force ohne override-reason wird abgelehnt
    Given Phase 5 von SPEC-0014 ist noch offen
    When "sdd execute SPEC-0014 --force" ohne --override-reason ausgeführt wird
    Then ist der Exit-Code 1
    And der Output enthält "--override-reason ist erforderlich"
```

## 11. Offene Fragen

| # | Frage | Verantwortlich | Deadline |
|---|-------|----------------|----------|
| OQ-01 | Soll der Konflikt-Cache auf Datei-Hash oder Datei-Timestamp basieren? | Boris | vor Contract-Schreiben |
| OQ-02 | Werden LLM-Critique-Items mit IDs versehen (für dismiss-Tracking)? | Boris | Phase 2 Design |
| OQ-03 | Wie werden generierte Tests versioniert wenn der Contract sich ändert? Neu generieren oder diff? | Boris | vor Test-Generierung |
| OQ-04 | Reicht ein `pipeline_phase`-Feld oder brauchen wir ein separates State-Machine-Objekt im Pipeline-JSON? | Boris | Architekturentscheidung |
