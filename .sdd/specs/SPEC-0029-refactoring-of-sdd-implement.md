---
id: SPEC-0029
title: Refactoring of sdd-implement
type: feature
status: in-progress
owner: Boris
created: 2026-05-29
updated: '2026-05-29'
version: 0.1.0
priority: medium
tags: []
depends_on: []
contracts:
- CON-0111
- CON-0112
- CON-0113
tests:
- TST-0130
- TST-0131
- TST-0132
adrs: []
started_at: '2026-05-29T22:13:20Z'
---
# Refactoring of sdd-implement

> **Status:** draft · **Owner:** Boris · **Version:** 0.1.0

## 1. Kontext & Motivation

/sdd-implement braucht eine Überarbeitung. Der ganze Flow scheint etwas buggy zu sein.

### Soll-Flow (Schritt für Schritt)

1. **Spec anlegen** (`/sdd-new spec`): Das LLM führt durch die Fragen. Das Spec bekommt den Zustand `draft`. Eine Validierung macht an dieser Stelle noch keinen Sinn — es existieren noch nicht genug Dokumente.
2. **Spec-Review** (`/sdd-review SPEC-XXXX`): Teilt sich in drei Schritte auf:
   - SOLID-Check: `sdd solid-check` → Spec wird auf SOLID-Principles geprüft und ergänzt
   - Pattern-Check: `sdd pattern-suggest` → Spec wird auf Design Patterns geprüft und ergänzt
   - Regression-Check (neu): Prüfung ob das neue Feature bestehende Specs/Contracts bricht
3. **Contracts anlegen** (`/sdd-new contract`): Basierend auf dem Spec werden Contracts erstellt.
4. **Contract-Review** (`/sdd-review CON-XXXX`): Jeder Contract wird einzeln geprüft — **vor** dem Schreiben von Tests. Kontext: das Spec + alle anderen Contracts des Specs. Im Review werden Probleme erkannt und der Contract "gehärtet". Erst nach erfolgtem Review wird der Contract auf `approved` gesetzt. Kein Test darf für einen Contract geschrieben werden, der noch nicht reviewed ist.
5. **Tests schreiben** (`/sdd-new test`): Für jeden Contract werden Tests erstellt. Die Tests orientieren sich am Techstack des Projekts. Bei einem neuen Projekt muss der Techstack im Spec definiert sein. Tests werden einem Review unterzogen (Kontext: Contract + Spec).
6. **Validierung** (`sdd validate SPEC-XXXX`): Letzte Prüfung der referenziellen Integrität. Bei Fehlern: beheben und erneut validieren. Erst wenn sauber → weiter.
7. **Decompose** (`sdd decompose SPEC-XXXX`): Zerlegt die Spec in klassifizierte Tasks. Dient in `/sdd-implement` als **Implementierungsplan** für Claude (sequenziell, manuell guided). Für den automatisierten LLM-Pool-Betrieb nutzt `sdd orchestrate` dieselben Tasks zur Verteilung (`sdd distribute`).
8. **Implementierung** (`/sdd-implement SPEC-XXXX`): Führt eigenständig aus:
   - `sdd spec approve SPEC-XXXX`
   - `sdd start SPEC-XXXX` (Status → `in-progress`)
   - Feature-Branch erstellen
   - Decompose-Tasks als Implementierungsplan laden
   - Code schreiben (Task für Task)
   - Container starten
   - Im Container testen (`sdd dev exec pytest`)
   - Code anpassen bis grün
   - `sdd finalize` (startet den Container nicht selbst — Container läuft bereits)

## 2. Zielsetzung

**Primärziel:**
Konsistenten, lückenlosen SDD-Implementierungsflow definieren und in den betroffenen Skills (`sdd-new`, `sdd-review`, `sdd-implement`) umsetzen.

**Erfolgskriterien (messbar):**

- [ ] `/sdd-new spec` ruft nach dem Speichern keine `sdd validate` auf
- [ ] `/sdd-review` umfasst drei dokumentierte Schritte: SOLID-Check, Pattern-Check, Regression-Check
- [ ] Contract-Review (`/sdd-review CON-XXXX`) ist mandatory Gate vor Test-Erstellung: kein Test ohne approved Contract
- [ ] Contract-Review lädt explizit das Spec + alle anderen Contracts desselben Specs als Kontext
- [ ] Test-Review ist eigenständiger Schritt im Skill (Kontext: Contract + Spec)
- [ ] `/sdd-implement` führt `sdd start`, Branch-Erstellung, Decompose-Plan-Load und `sdd finalize` eigenständig aus
- [ ] `sdd finalize` startet keinen Container selbst — setzt laufenden Container voraus

**Nicht-Ziele (explizit):**

- Änderungen am Python-CLI-Code (außer `sdd finalize` Container-Startlogik entfernen)
- Umbau von `sdd orchestrate` / `sdd distribute` (nutzen `decompose` bereits korrekt)
- Neue LLM-Features oder Modell-Änderungen

## 3. User Stories

| ID    | Als ...    | möchte ich ...                                                   | um ...                                                        |
| ----- | ---------- | ---------------------------------------------------------------- | ------------------------------------------------------------- |
| US-01 | Entwickler | nach `/sdd-new spec` sofort mit dem Inhalt arbeiten              | ohne durch vorzeitige Validierungsfehler abgelenkt zu werden  |
| US-02 | Entwickler | im Review auch einen Regression-Check erhalten                   | um Konflikte mit bestehenden Specs/Contracts früh zu erkennen |
| US-03 | Entwickler | `/sdd-implement` einmal starten                                  | um den gesamten TDD-Zyklus automatisch durchzulaufen          |
| US-04 | Entwickler | `sdd decompose` als strukturierten Implementierungsplan erhalten | um Task für Task gezielt implementieren zu können             |

## 4. Funktionale Anforderungen

- **FR-01:** `/sdd-new spec` speichert das Dokument und gibt einen Hinweis auf `/sdd-review SPEC-XXXX` aus — kein `sdd validate`-Aufruf.
- **FR-02:** `/sdd-review` gliedert sich in drei Unterschritte: (1) `sdd solid-check`, (2) `sdd pattern-suggest`, (3) `sdd regression-check SPEC-XXXX`.
- **FR-03:** `sdd regression-check SPEC-XXXX` arbeitet in zwei Stufen:
  - **Stufe 1 – Regelbasiert (deterministisch):** Prüft alle Contracts des Specs gegen Contracts aller anderen Specs mit `status: implemented`. Basisregeln v1:
    - _Endpoint-Konflikt:_ Zwei Contracts definieren dieselbe HTTP-Methode + Pfad
    - _Lifecycle-Konflikt:_ Ein Contract setzt einen Status voraus, den ein anderer Contract verbietet
    - _Schema-Konflikt:_ Zwei Contracts referenzieren dasselbe Feld mit inkompatiblen Typen
  - **Stufe 2 – LLM-Bewertung:** Das LLM bewertet die Regel-Ergebnisse (Falsch-Positive herausfiltern, semantische Konflikte in unklaren Fällen erkennen) und gibt eine finale Einschätzung mit Severity (`error` / `warning` / `ok`) aus.
  - Ausgabe: Liste der Konflikte mit betroffenen CON-IDs, Specs und Severity; bei 0 Konflikten: `✓ Kein Regressionsrisiko gefunden`.
- **FR-04:** Contract-Review im `/sdd-review`-Skill lädt als Kontext: das verknüpfte Spec + alle anderen Contracts desselben Specs.
- **FR-05:** Test-Review ist ein eigener Schritt nach `/sdd-new test` — Kontext: zugehöriger Contract + Spec.
- **FR-06:** `/sdd-implement` führt automatisch `sdd start SPEC-XXXX` aus wenn der Status noch nicht `in-progress` ist.
- **FR-07:** `/sdd-implement` erstellt automatisch einen Feature-Branch `feat/SPEC-XXXX` falls dieser noch nicht existiert.
- **FR-08:** `/sdd-implement` lädt die Decompose-Tasks via `sdd decompose SPEC-XXXX` (oder aus bestehendem Cache) als sequenziellen Implementierungsplan.
- **FR-09:** `/sdd-implement` ruft am Ende `sdd finalize SPEC-XXXX` auf; der Container muss zu diesem Zeitpunkt bereits laufen. Beim dritten fehlgeschlagenen Finalize-Versuch schlägt `/sdd-implement` automatisch `sdd finalize SPEC-XXXX --skip-container` vor.
- **FR-10:** `sdd finalize` bricht mit explizitem Fehler ab wenn kein Container läuft: `"✗ Dev-Container nicht gefunden – starte ihn mit 'sdd start SPEC-XXXX'"`. Mit `--skip-container` wird der Container-Check und der Container-Testlauf übersprungen; alle anderen Schritte (Commit, PR) laufen normal durch.

## 5. Nicht-funktionale Anforderungen

| Kategorie     | Anforderung                                                                                         |
| ------------- | --------------------------------------------------------------------------------------------------- |
| Konsistenz    | Alle Skills verwenden dieselbe Schritt-Terminologie (start → branch → decompose → TDD → finalize)   |
| Observability | Jeder Auto-Schritt in `/sdd-implement` gibt eine Statuszeile aus (z.B. `▶ sdd start …`)             |
| Backward Comp | Bestehende Specs mit `status: in-progress` können weiterhin mit `/sdd-implement` verarbeitet werden |

## 6. Akzeptanzkriterien (Gherkin)

```gherkin
Feature: Spec anlegen ohne vorzeitige Validierung

  Scenario: Neue Spec wird gespeichert
    Given kein Contract und kein Test für SPEC-XXXX existieren
    When /sdd-new spec durchgeführt und bestätigt wird
    Then wird die Spec-Datei gespeichert
    And sdd validate wird NICHT aufgerufen
    And ein Hinweis auf "/sdd-review SPEC-XXXX" wird ausgegeben

Feature: sdd regression-check findet Konflikte

  Scenario: Endpoint-Konflikt zwischen zwei Specs
    Given SPEC-0029 hat CON-0111 mit "POST /api/specs"
    And SPEC-0001 (implemented) hat CON-0001 mit "POST /api/specs"
    When sdd regression-check SPEC-0029 ausgeführt wird
    Then meldet Stufe 1 einen Endpoint-Konflikt: CON-0111 vs. CON-0001
    And das LLM bewertet den Konflikt als "error"
    And der Exit-Code ist 1

  Scenario: Kein Konflikt vorhanden
    Given SPEC-0029 hat Contracts die keine anderen Specs berühren
    When sdd regression-check SPEC-0029 ausgeführt wird
    Then erscheint "✓ Kein Regressionsrisiko gefunden"
    And der Exit-Code ist 0

Feature: sdd-implement als vollständiger Auto-Flow

  Scenario: Happy Path – Spec ist approved, Container läuft
    Given SPEC-XXXX hat status: approved
    And alle zugehörigen Contracts sind approved
    And Test-Stubs existieren
    And der Dev-Container läuft
    When /sdd-implement SPEC-XXXX aufgerufen wird
    Then wird sdd start SPEC-XXXX ausgeführt (Status → in-progress)
    And ein Feature-Branch feat/SPEC-XXXX wird erstellt oder ausgecheckt
    And sdd decompose SPEC-XXXX wird als Implementierungsplan geladen
    And der TDD-Zyklus wird Task für Task ausgeführt
    And sdd finalize SPEC-XXXX wird am Ende aufgerufen

  Scenario: Container läuft nicht beim Start
    Given SPEC-XXXX ist approved
    And der Dev-Container ist NICHT gestartet
    When /sdd-implement SPEC-XXXX aufgerufen wird
    Then erscheint "Container nicht gestartet – führe 'sdd start SPEC-XXXX' aus"
    And der Flow stoppt ohne Code zu schreiben

  Scenario: Dritter fehlgeschlagener Finalize-Versuch
    Given SPEC-XXXX ist in-progress
    And sdd finalize ist bereits 2x fehlgeschlagen
    And der Dev-Container läuft nicht mehr
    When /sdd-implement den dritten Finalize-Versuch startet
    Then wird "sdd finalize SPEC-XXXX --skip-container" vorgeschlagen
    And nach Bestätigung läuft Commit und PR ohne Container-Testlauf durch

Feature: sdd finalize – expliziter Container-Fehler

  Scenario: Kein Container beim Finalize
    Given SPEC-XXXX ist in-progress
    And kein Dev-Container für SPEC-XXXX läuft
    When sdd finalize SPEC-XXXX aufgerufen wird
    Then erscheint "✗ Dev-Container nicht gefunden – starte ihn mit 'sdd start SPEC-XXXX'"
    And der Exit-Code ist 1

  Scenario: Finalize mit --skip-container
    Given SPEC-XXXX ist in-progress
    And kein Dev-Container läuft
    When sdd finalize SPEC-XXXX --skip-container aufgerufen wird
    Then wird der Container-Check übersprungen
    And Commit und PR werden normal durchgeführt
    And eine Warnung erscheint: "⚠ Container-Tests wurden übersprungen"
```

## 7. Edge Cases & Fehlerfälle

- **Decompose liefert leere Task-Liste:** Fehlermeldung "Keine Tasks gefunden – prüfe Spec-Inhalt", Flow stoppt.
- **Status ist noch `draft`:** Hinweis auf fehlende Schritte (Review, Contracts, Tests, Validierung).
- **Feature-Branch existiert bereits:** Checkout ohne Fehler, kein neuer Branch.
- **`sdd finalize` schlägt fehl (kein Container):** Expliziter Fehler mit Hinweis auf `sdd start SPEC-XXXX`. Bei drittem Fehlversuch: `/sdd-implement` schlägt `--skip-container` vor; nach Bestätigung laufen Commit + PR ohne Container-Testlauf durch, mit sichtbarer Warnung.
- **`--skip-container` ohne vorherige Tests:** Warnung wird ausgegeben; kein automatisches Abbrechen, da der Entwickler die Entscheidung bewusst trifft.
- **Regression-Check findet Konflikte:** Stufe-1-Regeln melden Treffer → LLM bewertet → Ausgabe mit Severity. Entwickler entscheidet ob Spec anpassen oder Falsch-Positiv ignorieren.
- **Keine implementierten Specs vorhanden:** Regression-Check gibt `✓ Keine implementierten Specs zum Vergleich` aus und endet mit Exit-Code 0.
- **LLM nicht verfügbar:** Stufe-1-Ergebnisse werden ohne LLM-Bewertung ausgegeben; alle unklaren Fälle erhalten Severity `warning`.

## 8. Contracts (was wird garantiert)

Diese Spec wird durch folgende Contracts maschinell prüfbar gemacht:

| Contract-ID | Typ      | Was wird garantiert?                                                                    |
| ----------- | -------- | --------------------------------------------------------------------------------------- |
| CON-0111    | behavior | `/sdd-new spec` ruft nach dem Speichern keine `sdd validate` auf                        |
| CON-0112    | behavior | `/sdd-review` führt SOLID-Check, Pattern-Check und Regression-Check durch               |
| CON-0113    | behavior | `/sdd-implement` führt start, Branch, Decompose-Plan, TDD und finalize eigenständig aus |

## 9. Tests (wie wird verifiziert)

| Test-ID  | Level      | Was prüft der Test?                                                                         |
| -------- | ---------- | ------------------------------------------------------------------------------------------- |
| TST-0130 | acceptance | `sdd-new`-Skill enthält nach Speichern keinen `sdd validate`-Aufruf (CON-0111)              |
| TST-0131 | acceptance | `sdd-review`-Skill dokumentiert alle drei Review-Schritte inkl. Regression-Check (CON-0112) |
| TST-0132 | acceptance | `sdd-implement`-Skill führt den vollständigen Auto-Flow aus (CON-0113)                      |

## 10. Offene Fragen

- [x] Regression-Check wird als CLI-Befehl `sdd regression-check SPEC-XXXX` implementiert (→ FR-03)
- [x] `sdd finalize` bricht mit explizitem Fehler ab wenn kein Container läuft; Workaround beim 3. Versuch: `--skip-container` überspringt Container-Check + Testlauf (→ FR-10)

## 11. Änderungshistorie

| Datum      | Version | Autor | Änderung                                                 |
| ---------- | ------- | ----- | -------------------------------------------------------- |
| 2026-05-29 | 0.1.0   | Boris | Initiale Erstellung + Flow-Definition                    |
| 2026-05-29 | 0.2.0   | Boris | decompose als Planungstool, orchestrate für Distribution |
