---
id: SPEC-0006
title: "Test Run Results"
status: implemented     # draft | review | approved | implemented | deprecated
owner: "Boris"
created: 2026-05-12
updated: 2026-05-12
version: 1.0.0
implementation_status: ready_to_implement
priority: medium        # low | medium | high | critical
tags: ["cli", "web", "testing", "quality"]
depends_on: []
contracts: ["CON-0017", "CON-0018", "CON-0019"]
tests: ["TST-0017", "TST-0018", "TST-0019", "TST-0020", "TST-0021", "TST-0022", "TST-0023", "TST-0024"]
adrs: []
---

# Test Run Results

> **Status:** implemented · **Owner:** Boris · **Version:** 1.0.0

## 1. Kontext & Motivation

Im SDD-System sind alle Tests (TST-XXXX) über Frontmatter-Referenzen direkt mit Specs und Contracts verknüpft.
Bisher gibt es keine Möglichkeit, diese Tests tatsächlich auszuführen und die Ergebnisse spec-bezogen einzusehen.

Der Entwickler muss heute manuell `pytest` aufrufen und die Ausgabe selbst interpretieren.
Es ist nicht ersichtlich, welche Tests zu welcher Spec gehören, welche Contracts abgedeckt sind
und ob die Qualität eines Features im Zeitverlauf zu- oder abnimmt.

Diese Spec beschreibt die Fähigkeit, Test-Runs pro Spec auszulösen und die Ergebnisse strukturiert
abrufbar zu machen – über CLI, Web API und (perspektivisch) VS Code Extension.

## 2. Zielsetzung

**Primärziel:**
Einem Entwickler ermöglichen, mit einem einzigen Befehl alle Tests einer Spec auszuführen und
eine strukturierte Auswertung (Pass / Fail / Skip, Contract-Coverage, Fehlermeldungen) zu erhalten.

**Erfolgskriterien (messbar):**
- [ ] `sdd test-run SPEC-XXXX` führt alle verknüpften Tests aus und gibt Exit-Code 0 (alle grün) oder 1 (mind. ein Fehler) zurück
- [ ] `sdd test-results SPEC-XXXX` zeigt Ergebnisse des letzten Runs in < 500ms an
- [ ] Jeder Test-Run wird mit Timestamp und Dauer in `.sdd/test-runs/` persistiert
- [ ] Die Contract-Coverage (welche Contracts durch ≥ 1 grünen Test abgedeckt sind) ist im Report sichtbar
- [ ] Web API `GET /specs/{id}/test-results` liefert dieselben Daten als JSON

**Nicht-Ziele (explizit):**
- Kein eigenes Test-Framework – die CLI ruft `pytest` (oder konfigurierten Runner) auf
- Kein Live-Streaming von Test-Output (Ergebnisse erst nach Abschluss des Runs)
- Keine Benachrichtigungen / Webhooks bei Fehlern
- Kein Diff zwischen zwei Runs (Trend-Analyse ist spätere Erweiterung)

## 3. User Stories

| ID    | Als ...    | möchte ich ...                                                | um ...                                                         |
|-------|------------|---------------------------------------------------------------|----------------------------------------------------------------|
| US-01 | Entwickler | alle Tests einer Spec mit einem Befehl ausführen              | schnell zu sehen ob meine Implementierung vollständig ist      |
| US-02 | Entwickler | die Ergebnisse des letzten Runs pro Spec abrufen              | die Qualität eines Features ohne erneuten Run einzuschätzen   |
| US-03 | Entwickler | sehen welche Contracts noch nicht durch Tests abgedeckt sind  | gezielt fehlende Tests zu schreiben                            |
| US-04 | Entwickler | fehlgeschlagene Tests mit Fehlermeldung angezeigt bekommen    | den Fehler ohne zusätzliche Tools zu lokalisieren              |
| US-05 | CI/CD      | `sdd test-run --all` ausführen und Exit-Code auswerten        | den Build bei Testfehlern zu blockieren                        |

## 4. Funktionale Anforderungen

- **FR-01:** `sdd test-run [SPEC-ID]` führt alle Tests aus, die im Frontmatter der Spec unter `tests:` referenziert sind. Für jeden TST-ID wird das TST-Dokument geladen und das `artifact:`-Feld ausgelesen; dieses enthält den Pfad zur ausführbaren Testdatei (z. B. `tests/unit/test_auth.py`).
- **FR-02:** `sdd test-run --all` führt alle Tests aller Specs im Projekt sequenziell aus.
- **FR-03:** Das Ergebnis eines Runs (Pass/Fail/Skip/Error je Test, Gesamt-Dauer, Timestamp) wird als JSON unter `.sdd/test-runs/{SPEC-ID}-{timestamp}.json` gespeichert.
- **FR-04:** `sdd test-results [SPEC-ID]` liest den neuesten gespeicherten Run und gibt ihn als formatierte Tabelle aus.
- **FR-05:** Die Ausgabe enthält eine Contract-Coverage-Zeile: welche Contracts der Spec durch ≥ 1 grünen Test abgedeckt sind.
- **FR-06:** Bei fehlgeschlagenen Tests wird die Fehlermeldung (pytest short-repr) im Report angezeigt.
- **FR-07:** Fehlt ein referenziertes TST-Dokument oder ist sein `artifact:`-Feld ein unausgefüllter Platzhalter (`tests/<level>/...`), wird der Test im Report als `status: missing` markiert (kein Abbruch). Betrifft aktuell TST-0005, TST-0006, TST-0007, TST-0016.
- **FR-08:** Tests mit nicht-pytest-Artefakten (`.feature`, `.k6.js`, `.spec.ts`) werden im Report als `status: skipped (runner: unsupported)` markiert; kein Fehler, kein Exit-Code 1. Betrifft aktuell TST-0002 (Gherkin), TST-0004 (k6), TST-0014 (Playwright).
- **FR-09:** `GET /specs/{id}/test-results` in der Web API liefert den letzten Run als JSON (identische Datenstruktur wie FR-03).
- **FR-10:** `POST /specs/{id}/test-run` in der Web API löst einen Run aus und gibt das Ergebnis synchron zurück (Timeout: 120 s).

## 5. Nicht-funktionale Anforderungen

| Kategorie     | Anforderung                                                              |
|---------------|--------------------------------------------------------------------------|
| Performance   | `sdd test-results` liefert Ausgabe in < 500 ms (nur Lesen, kein Run)    |
| Performance   | Web API `GET /test-results` antwortet in < 200 ms p95                   |
| Persistenz    | Run-JSONs werden nie automatisch gelöscht; max. 50 Dateien pro Spec (älteste rotation) |
| Portabilität  | Konfigurierter Test-Runner (Standard: `pytest`) in `.sdd/config.yaml`   |
| Observability | Jeder Run-JSON enthält: `spec_id`, `runner`, `started_at`, `duration_s`, `exit_code` |
| CI-Eignung    | Exit-Code 0 = alle Tests grün, 1 = mind. ein Fehler, 2 = Konfigurationsfehler |

## 6. Akzeptanzkriterien (Gherkin)

```gherkin
Feature: Test Run Results

  Scenario: Test-Run für eine Spec auslösen
    Given eine Spec SPEC-0001 mit den Tests TST-0001 und TST-0002
    And beide Test-Dateien existieren im Filesystem
    When der Entwickler `sdd test-run SPEC-0001` ausführt
    Then werden TST-0001 und TST-0002 via pytest ausgeführt
    And das Ergebnis wird unter `.sdd/test-runs/SPEC-0001-*.json` gespeichert
    And der Exit-Code ist 0 wenn alle Tests grün sind

  Scenario: Ergebnisübersicht abrufen
    Given ein gespeicherter Test-Run für SPEC-0001
    When der Entwickler `sdd test-results SPEC-0001` ausführt
    Then wird eine Tabelle mit Pass/Fail/Skip-Anzahl angezeigt
    And die Contract-Coverage zeigt welche Contracts abgedeckt sind

  Scenario: Fehlgeschlagener Test im Report
    Given ein Test-Run für SPEC-0001 bei dem TST-0002 fehlschlug
    When der Entwickler `sdd test-results SPEC-0001` ausführt
    Then wird TST-0002 als FAIL markiert
    And die Fehlermeldung von TST-0002 wird unterhalb der Tabelle ausgegeben

  Scenario: Spec ohne verknüpfte Tests
    Given eine Spec SPEC-0005 mit leerem `tests:`-Frontmatter
    When der Entwickler `sdd test-run SPEC-0005` ausführt
    Then wird die Warnung "Keine Tests verknüpft – nichts auszuführen" angezeigt
    And der Exit-Code ist 2

  Scenario: Test-Run über Web API auslösen
    Given die Web API läuft
    When `POST /specs/SPEC-0001/test-run` aufgerufen wird
    Then werden alle verknüpften Tests ausgeführt
    And die Antwort enthält das vollständige Run-JSON mit exit_code
```

## 7. Edge Cases & Fehlerfälle

- **Referenzierter Test fehlt im Filesystem:** Test wird im Report als `status: missing` geführt, Run läuft weiter.
- **Test-Runner nicht installiert:** Fehlermeldung "pytest nicht gefunden – bitte installieren oder runner in .sdd/config.yaml konfigurieren." Exit-Code 2.
- **Leeres `tests:`-Frontmatter:** Warnung, Exit-Code 2, kein Run-JSON wird angelegt.
- **Timeout bei Web API (> 120 s):** HTTP 504, kein Run-JSON persistiert.
- **Kein bisheriger Run vorhanden:** `sdd test-results SPEC-XXXX` gibt "Noch kein Test-Run gefunden. Starte mit `sdd test-run SPEC-XXXX`." aus.
- **`.sdd/test-runs/` nicht schreibbar:** Fehlermeldung mit Pfad, Exit-Code 2.
- **Rotation:** Wenn > 50 Runs für eine Spec existieren, wird der älteste gelöscht bevor der neue angelegt wird.

## 8. Contracts (was wird garantiert)

Diese Spec wird durch folgende Contracts maschinell prüfbar gemacht:

| Contract-ID | Typ         | Was wird garantiert?                                                   |
|-------------|-------------|------------------------------------------------------------------------|
| CON-XXXX    | api         | `GET /specs/{id}/test-results` und `POST /specs/{id}/test-run` Schema |
| CON-XXXX    | behavior    | Gherkin-Szenarien aus Sektion 6                                        |
| CON-XXXX    | performance | Web API p95 < 200 ms für `GET /test-results`                          |

## 9. Tests (wie wird verifiziert)

| Test-ID  | Level      | Was prüft der Test?                                            |
|----------|------------|----------------------------------------------------------------|
| TST-XXXX | unit       | Run-JSON-Serialisierung / Deserialisierung                     |
| TST-XXXX | unit       | Rotation: > 50 Runs löscht ältesten                           |
| TST-XXXX | unit       | Edge Case: leeres `tests:`-Frontmatter → Exit-Code 2          |
| TST-XXXX | unit       | Edge Case: fehlender Test → Status `missing` im Report        |
| TST-XXXX | contract   | OpenAPI-Konformität `GET /test-results` gegen CON-XXXX        |
| TST-XXXX | contract   | OpenAPI-Konformität `POST /test-run` gegen CON-XXXX           |
| TST-XXXX | acceptance | Gherkin-Szenarien aus Sektion 6 vollständig durchgespielt      |
| TST-XXXX | performance| `GET /test-results` p95 < 200 ms unter Last (10 rps, 30 s)    |

## 10. Offene Fragen

- [x] **Runner konfigurierbar?** → Ja. `test_runner.command` in `.sdd/config.yaml` einführen, Default `pytest`. Nur pytest wird in v1 aktiv ausgeführt; andere Artefakt-Typen erhalten `status: skipped` (FR-08). *(Entschieden bei Implementierungsanalyse 2026-05-12)*
- [x] **VS Code Code Lens "▶ Run Tests"?** → Eigene Spec, nicht SPEC-0006. *(Entschieden bei Implementierungsanalyse 2026-05-12)*
- [ ] Soll `sdd test-results` einen `--last N` Flag bekommen, um die letzten N Runs nebeneinander anzuzeigen?
- [ ] Placeholder-`artifact:` in TST-0005/0006/0007/0016 nachpflegen – wer, bis wann?

## 11. Änderungshistorie

| Datum      | Version | Autor   | Änderung                                                         |
|------------|---------|---------|------------------------------------------------------------------|
| 2026-05-12 | 0.1.0   | Boris   | Initiale Erstellung (Skeleton)                                   |
| 2026-05-12 | 0.2.0   | Boris   | Vollständige Ausarbeitung aller Sektionen                        |
| 2026-05-12 | 0.3.0   | Boris   | Implementierungsanalyse integriert: FRs präzisiert, Blocker dokumentiert, offene Fragen entschieden |
| 2026-05-12 | 1.0.0   | Boris   | Vollständig implementiert: CLI, Web API, Web UI (TestRunPanel), Contracts, Tests |

## 12. Implementierungsplan

Ergebnis der Codebase-Analyse vom 2026-05-12. Alle Punkte sind Implementierungsarbeit — keine architektonischen Blocker.

### Echte Blocker (ohne diese kein lauffähiges Feature)

**B1 — Neues CLI-Modul `tool/sdd_cli/test_runner.py`**
Enthält die gesamte Kernlogik:
- TST-IDs aus Spec-Frontmatter lesen
- TST-Dokument laden → `artifact:` auflösen
- `pytest <artifact>` via `subprocess` aufrufen, JSON-Output parsen (`--json-report`)
- Run-JSON serialisieren und unter `.sdd/test-runs/` ablegen
- Rotation: wenn > 50 Runs für eine Spec, älteste Datei löschen

**B2 — Neue CLI-Commands in `tool/sdd_cli/main.py`**
```python
@cli.command("test-run")   # sdd test-run [SPEC-ID] [--all]
@cli.command("test-results")  # sdd test-results [SPEC-ID]
```
Delegieren an `test_runner.py`. Exit-Codes wie in NFR definiert.

**B3 — Neue Web-API-Routen in `web/api/routes/tests.py`**
```
GET  /specs/{spec_id}/test-results   → letzten Run lesen
POST /specs/{spec_id}/test-run       → Run auslösen, synchron warten (120 s Timeout)
```

### Soft-Blocker (einfach, aber notwendig)

**S1 — `SddConfig.test_runs_dir` Property** in `tool/sdd_cli/config.py`
```python
@property
def test_runs_dir(self) -> Path:
    return self.sdd_dir / "test-runs"
```

**S2 — `test_runner`-Block in `.sdd/config.yaml`**
```yaml
test_runner:
  command: pytest          # Standard-Runner
  extra_args: []           # z.B. ["-x", "--tb=short"]
  timeout_per_spec: 120    # Sekunden
```
`SddConfig` braucht einen Accessor `runner_command() -> str`.

### Reihenfolge

```
S1 → S2 → B1 → B2 → B3
```

S1 und S2 sind Voraussetzung für B1; B2 und B3 können parallel nach B1 erfolgen.

### Bekannte Einschränkungen v1

| TST-Dokument | Grund | Behandlung |
|---|---|---|
| TST-0005, TST-0006, TST-0007, TST-0016 | `artifact:` ist Platzhalter | `status: missing` |
| TST-0002 | `.feature`-Artefakt (Gherkin/Behave) | `status: skipped` |
| TST-0004 | `.k6.js`-Artefakt (k6 Load Test) | `status: skipped` |
| TST-0014 | `.spec.ts`-Artefakt (Playwright) | `status: skipped` |
