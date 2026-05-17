---
id: SPEC-0010
project: PRJ-0001
title: Content-Update-Lifecycle – Statusübergänge und LLM-gestützte Contract-Absicherung
status: implemented
owner: Boris
created: 2026-05-14
updated: 2026-05-14
version: 0.1.0
priority: high
tags:
- status-machine
- workflow
- llm
- contracts
- automation
- review
depends_on:
- SPEC-0008
contracts:
- CON-0037
- CON-0038
- CON-0039
- CON-0040
tests:
- TST-0048
- TST-0049
- TST-0050
- TST-0051
- TST-0052
- TST-0053
- TST-0054
adrs: []
---
# Content-Update-Lifecycle – Statusübergänge und LLM-gestützte Contract-Absicherung

> **Status:** draft · **Owner:** Boris · **Version:** 0.1.0

## 1. Kontext & Motivation

Im aktuellen SDD-System sind Spec- und Contract-Status (`draft`, `review`, `approved`,
`implemented`) manuell gesetzte Felder. Eine inhaltliche Änderung an einem Artefakt löst
keinen automatischen Statusübergang aus – der Entwickler muss selbst daran denken, den
Status zurückzusetzen.

Das führt zu zwei konkreten Problemen:
1. **Stale Approvals:** Ein `approved`-Spec wird inhaltlich geändert (neue Anforderungen,
   überarbeitete Contracts), bleibt aber im Status `approved`. Consumers können nicht
   erkennen, dass eine Re-Review nötig ist.
2. **Unkontrollierte neue Contracts:** Ein neu erstellter oder inhaltlich erweiterter Contract
   hat keinen zugeordneten Test. Die Absicherung liegt allein in der Disziplin des Entwicklers.

Diese Spec definiert:
- Welche Content-Änderungen welche Statusübergänge erzwingen (Zustandsmaschine)
- Wie ein LLM automatisch ausgelöste Review-Tasks für neue/geänderte Contracts übernimmt
- Wie diese Tasks im System nachverfolgt werden

## 2. Zielsetzung

**Primärziel:**
Jede inhaltliche Änderung an einem Spec oder Contract hat eine definierte Auswirkung auf
den Status des Artefakts; neue Contracts werden automatisch von einem LLM geprüft und mit
Testvorschlägen versehen.

**Erfolgskriterien (messbar):**
- [ ] Eine Änderung am Body oder Frontmatter (außer `updated:`, `status:`) eines `approved`-Specs setzt Status auf `review`
- [ ] Ein neu erstellter Contract hat initial Status `review` (nicht `draft`)
- [ ] `sdd validate` meldet einen Fehler wenn ein Contract im Status `review` keinen verknüpften Test hat
- [ ] `sdd review-contract CON-XXXX` ruft das LLM auf, prüft den Contract und erzeugt einen Testvorschlag als TST-Datei mit Status `draft`
- [ ] `sdd review-pending` listet alle Contracts im Status `review` ohne abgedeckten Test
- [ ] Status-Übergänge werden in einem Audit-Log (`.sdd/audit.log`) festgehalten

**Nicht-Ziele (explizit):**
- Kein automatisches Mergen oder Approven durch das LLM (nur Vorschläge, Mensch entscheidet)
- Kein Enforcement von Statusübergängen bei manuellen Datei-Edits (Hooks sind optional, nicht erzwingend)
- Keine Echtzeit-Überwachung des Dateisystems (nur explizite CLI-Aufrufe oder Git-Hook)

## 3. Zustandsmaschine

```
             [create]           [edit body/fm]      [re-edit]
  (new)  ──────────→  draft  ──────────────→  review  ←──────────┐
                        │                       │                  │
                   [approve]               [approve]          [edit body/fm]
                        │                       │                  │
                        └──────────→  approved ─┘                  │
                                          │                        │
                                    [implement]               [implement]
                                          │                        │
                                          └──→  implemented ───────┘
```

**Übergänge:**

| Auslöser | Von Status | Nach Status | Bedingung |
|---|---|---|---|
| Neues Artefakt (`sdd new`) | – | `draft` | immer |
| Neuer Contract (`sdd new contract`) | – | `review` | immer (Contract braucht sofort Test) |
| Body-Edit erkannt | `approved` | `review` | YAML-Body oder Frontmatter (außer `updated:`/`status:`) geändert |
| Body-Edit erkannt | `implemented` | `review` | wie oben |
| `sdd approve SPEC-XXXX` | `draft` oder `review` | `approved` | manuell durch Owner |
| `sdd implement SPEC-XXXX` | `approved` | `implemented` | manuell durch Owner |
| Kein Rückschritt von `implemented` → `draft` (erfordert explizite Begründung via ADR) |

**Body-Edit-Erkennung:**
Ein Content-Update wird als "edit" gewertet wenn sich der SHA-256-Hash des Dateiinhalts
(ohne `updated:`-Zeile und ohne `status:`-Zeile) gegenüber dem letzten bekannten Hash ändert.
Hashes werden in `.sdd/content-hashes.json` gespeichert.

## 4. Funktionale Anforderungen

### Status-Tracking

- **FR-01:** `sdd status-check [--fix]` berechnet für jedes Artefakt den aktuellen Content-Hash,
  vergleicht mit `.sdd/content-hashes.json` und meldet alle Artefakte, deren Status veraltet ist.
  Mit `--fix` werden Status-Felder im Frontmatter automatisch aktualisiert.
- **FR-02:** Ein Git-Pre-Commit-Hook-Script (`sdd install-hooks`) ruft `sdd status-check --fix`
  auf, sodass Status-Updates bei jedem Commit automatisch korrekt sind.
- **FR-03:** Bei `sdd new contract` wird der initiale Status auf `review` gesetzt (nicht `draft`).
- **FR-04:** Jeder Status-Übergang schreibt einen Eintrag in `.sdd/audit.log`:
  `{timestamp} {artifact_id} {old_status} → {new_status} [{reason}]`

### LLM Contract-Review

- **FR-05:** `sdd review-contract CON-XXXX` sendet den vollständigen Contract-Inhalt plus
  Referenz-Spec an das konfigurierte LLM (via `SPEC-0008`-Provider) mit folgendem Auftrag:
  1. Vollständigkeits- und Konsistenzprüfung des Contracts
  2. Generierung von mindestens einem beschreibenden Test (Gherkin-Szenario oder
     pytest-Testgerüst, abhängig von Contract-Typ)
  3. Bewertung: `approved` (Contract ist klar und vollständig) oder `needs_revision`
     mit Begründung
- **FR-06:** Das LLM-Ergebnis wird als neue TST-Datei unter `tests/` gespeichert (Status `draft`,
  LLM-generiert markiert via `generated_by: llm` im Frontmatter) und mit dem Contract verknüpft.
- **FR-07:** Bewertet das LLM den Contract als `needs_revision`, werden die Hinweise als
  Kommentar-Block am Ende der Contract-Datei unter `## LLM Review Notes` eingefügt
  (nicht als Body-Überschreibung).
- **FR-08:** `sdd review-pending` listet alle Contracts mit Status `review` und ohne
  verknüpften Test (Contract-ID referenziert keine TST-Datei). Ausgabe als Tabelle:
  Contract-ID, Titel, zugehöriger Spec, Alter (Tage seit Erstellung).
- **FR-09:** `sdd review-pending --auto` führt `sdd review-contract` für jeden Eintrag
  der Pending-Liste sequenziell aus. Gibt Fortschritt als Rich-Progress-Bar aus.

### Validierung

- **FR-10:** `sdd validate` erhält eine neue Regel: Contract mit Status `review` ohne
  verknüpften Test → `ERROR: CON-XXXX hat Status 'review' aber keinen verknüpften Test`.
- **FR-11:** `sdd validate` erhält eine neue Regel: Spec mit Status `approved` und mindestens
  einem Contract im Status `review` → `WARNING: SPEC-XXXX hat approved-Status aber CON-XXXX ist noch in review`.

## 5. Nicht-funktionale Anforderungen

| Kategorie     | Anforderung                                                                                    |
|---------------|------------------------------------------------------------------------------------------------|
| Determinismus | Content-Hash berechnet ohne `updated:`- und `status:`-Zeile → idempotent bei reinen Status-Updates |
| Auditierbarkeit | Jeder Status-Übergang in `.sdd/audit.log` mit Timestamp und Grund                           |
| Testbarkeit   | LLM-Aufruf via `SPEC-0008`-Provider-Abstraktionsschicht → vollständig mockbar                 |
| Performance   | `sdd status-check` für 50 Artefakte in < 1 Sekunde                                            |
| Sicherheit    | LLM-Review-Ergebnis wird niemals direkt in Frontmatter `status:`-Feld geschrieben (nur Human-approved) |

## 6. Akzeptanzkriterien (Gherkin)

```gherkin
Feature: Content-Update erzeugt Statusübergang

  Scenario: Approved Spec wird geändert → Review
    Given SPEC-0001 hat Status approved
    And der Content-Hash ist in .sdd/content-hashes.json gespeichert
    When der Body von SPEC-0001 geändert wird
    And `sdd status-check --fix` ausgeführt wird
    Then hat SPEC-0001 Status review
    And .sdd/audit.log enthält den Übergang "approved → review"

  Scenario: Neuer Contract erhält direkt Status review
    Given ein SDD-Projekt mit SPEC-0001
    When `sdd new contract` für SPEC-0001 ausgeführt wird
    Then hat der neue Contract Status review (nicht draft)

  Scenario: LLM-Review erzeugt Test-Vorschlag
    Given CON-0001 hat Status review und keinen verknüpften Test
    When `sdd review-contract CON-0001` ausgeführt wird
    Then wird eine neue TST-Datei unter tests/ angelegt mit Status draft
    And die TST-Datei enthält generated_by: llm im Frontmatter
    And CON-0001 referenziert die neue TST-ID

  Scenario: validate meldet Contract ohne Test
    Given CON-0002 hat Status review und kein Test ist mit ihm verknüpft
    When `sdd validate` ausgeführt wird
    Then enthält die Ausgabe ERROR für CON-0002

  Scenario: status-check ohne Änderungen → kein Übergang
    Given alle Artefakte sind auf aktuellem Stand
    When `sdd status-check` ausgeführt wird
    Then gibt es keine vorgeschlagenen Status-Übergänge
    And der Exit-Code ist 0
```

## 7. Edge Cases & Fehlerfälle

- **E-01:** `.sdd/content-hashes.json` fehlt (Erstlauf) → `sdd status-check` berechnet alle Hashes neu und legt die Datei an; kein falscher Alarm.
- **E-02:** Contract hat `review`-Status, LLM nicht verfügbar → `sdd review-contract` gibt Fehlermeldung aus, Contract-Status bleibt unverändert, kein Teilschreiben.
- **E-03:** LLM generiert ungültiges Frontmatter für TST-Datei → TST-Datei wird nicht gespeichert, Fehlermeldung mit LLM-Output-Auszug.
- **E-04:** Status-Rückschritt `implemented → draft` via manuellem Edit → `sdd status-check` erkennt keine Notwendigkeit für Rückschritt (Hash-basiert); `sdd validate` meldet WARNING wenn `implemented`-Status ohne gültige Implementierung.
- **E-05:** Gleichzeitiger Edit desselben Artefakts (Race Condition im Watch-Modus von SPEC-0009) → letzter Schreiber gewinnt; kein Datenkorruptionsschutz auf Dateiebene (außerhalb des Scope).

## 8. Contracts (was wird garantiert)

| Contract-ID | Typ      | Was wird garantiert?                                         |
|-------------|----------|--------------------------------------------------------------|
| TBD         | behavior | Status-Übergangstabelle (§3) und Trigger-Bedingungen         |
| TBD         | data     | Schema von `.sdd/content-hashes.json`                        |
| TBD         | data     | Schema des LLM-generierten TST-Frontmatters                  |
| TBD         | behavior | `sdd validate`-Fehlerregeln FR-10/FR-11                      |

## 9. Tests (wie wird verifiziert)

| Test-ID | Level    | Was prüft der Test?                                                                    |
|---------|----------|----------------------------------------------------------------------------------------|
| TBD     | unit     | Content-Hash-Berechnung: `updated:` und `status:`-Zeilen werden ignoriert             |
| TBD     | unit     | Status-Übergang `approved → review` bei Hash-Änderung                                 |
| TBD     | unit     | Kein Übergang wenn nur `updated:` geändert wurde                                       |
| TBD     | unit     | `sdd new contract` → initiales Status = `review`                                       |
| TBD     | unit     | Audit-Log-Schreibung bei jedem Übergang                                                |
| TBD     | unit     | `review-contract` mockt LLM via Provider-Abstraktionsschicht; prüft TST-Datei-Output  |
| TBD     | unit     | `validate` meldet ERROR für Contract(review) ohne Test (FR-10)                        |
| TBD     | acceptance | Gherkin-Szenarien aus §6 vollständig durchgespielt                                  |

## 10. Offene Fragen

- [ ] Soll der Content-Hash auch Änderungen an referenzierten Contracts/Tests erfassen (transitiver Hash)?
- [ ] Wie wird mit Umbenennung von Dateien umgegangen? ID bleibt gleich, Pfad ändert sich → Hash-Lookup nach ID, nicht nach Pfad?
- [ ] Soll `sdd review-contract --all-review` als Alias für `sdd review-pending --auto` eingeführt werden?
- [ ] LLM-Review-Qualität: Soll das Review-Ergebnis in `.sdd/evaluations.db` gespeichert werden (für SPEC-0011 Kostenschätzung)?

## 11. Änderungshistorie

| Datum      | Version | Autor | Änderung              |
|------------|---------|-------|-----------------------|
| 2026-05-14 | 0.1.0   | Boris | Initiale Erstellung   |
