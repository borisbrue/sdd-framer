---
id: SPEC-0019
title: "TDD-Implementierungsphase – status: in-progress + sdd start als formalisierter Entwicklungsschritt"
status: implemented
owner: Boris
created: 2026-05-16
updated: 2026-05-16
version: 0.1.0
priority: high
tags:
  - tdd
  - lifecycle
  - workflow
  - implementation-phase
  - status-transition
depends_on:
  - SPEC-0010
  - SPEC-0014
contracts:
  - CON-0060
  - CON-0061
  - CON-0062
tests:
  - TST-0069
  - TST-0070
  - TST-0071
adrs: []
---

# TDD-Implementierungsphase – status: in-progress + sdd start

> **Status:** implemented · **Owner:** Boris · **Version:** 0.1.0

## 1. Kontext & Motivation

Der aktuelle SDD-Lifecycle-Flow hat eine Lücke zwischen Execution Gate und `implemented`:

```
approved (Gate bestanden) → ??? → implemented
```

Es gibt keinen formalisierten Schritt für die eigentliche Implementierung. Das führt zu drei
Problemen:

1. **Keine Sichtbarkeit:** `sdd status-check` kann nicht unterscheiden, ob eine Spec
   gerade aktiv entwickelt wird oder vergessen wurde.
2. **Falsche Reihenfolge möglich:** Ohne Formalisierung besteht kein Hinweis darauf,
   dass Tests *vor* dem Code angelegt werden sollen (TDD). Der Entwickler baut Code und
   schreibt Tests nachträglich – die Contracts verlieren ihre Bindekraft.
3. **Kein klarer Einstiegspunkt:** Nach dem Gate ist unklar, was der nächste konkrete
   Schritt ist.

**Die Lösung:** Ein neuer Status `in-progress` und ein Befehl `sdd start SPEC-XXXX`,
der den Entwickler durch den TDD-Einstieg führt: Test-Stubs anlegen, dann Code schreiben.

---

## 2. Zielsetzung

**Primärziel:**
Der Übergang von `approved` (Gate bestanden) zu `implemented` ist explizit, sichtbar
und TDD-konform: Tests existieren vor dem Code.

**Erfolgskriterien (messbar):**

- [ ] `sdd start SPEC-XXXX` setzt Status auf `in-progress` und gibt eine geordnete
      Checkliste der zu schreibenden Tests aus (aus verknüpften Contracts)
- [ ] `sdd status-check` zeigt `in-progress`-Specs in eigener Sektion mit Zeitstempel
      (wann wurde `start` aufgerufen?)
- [ ] `validate.py` akzeptiert `in-progress` als gültigen Status nach `approved`
      und vor `implemented`
- [ ] Ein `in-progress`-Spec ohne verknüpfte Test-Dateien nach 24 h löst eine
      `[WARN]`-Meldung in `sdd status-check` aus
- [ ] Der Lifecycle `approved → in-progress → implemented` ist der einzig erlaubte
      Vorwärts-Übergang; Rücksprung zu `draft` bleibt erlaubt

**Nicht-Ziele:**
- Kein automatisches Test-Ausführen (das ist Aufgabe der CI-Pipeline)
- Kein Erzwingen von Test-Coverage-Metriken
- Kein Blockieren von `sdd status → implemented` wenn Tests rot sind
  (SDD prüft Dokumente, nicht Code-Ausführung)
- Kein Ersetzen von SPEC-0014 Execution Gate – `start` setzt dessen erfolgreichen
  Abschluss voraus

---

## 3. Architektur & Design

### 3.1 Erweiterter Lifecycle

```
draft → in-review → approved → in-progress → implemented
                ↓                    ↓
             (rejected)           (draft)  ← Rücksprung erlaubt
```

### 3.2 `sdd start` – Ablauf

```
sdd start SPEC-XXXX
  1. Prüfe: status == approved (sonst Fehler)
  2. Prüfe: Execution Gate wurde durchlaufen (pipeline.json existiert + alle Phasen grün)
  3. Setze status → in-progress, schreibe started_at: <ISO-Datum>
  4. Lies verknüpfte Test-IDs + Contracts aus Frontmatter
  5. Erzeuge Test-Stub-Dateien für jeden verknüpften TST-XXXX:
     - tests/unit/test_<slug>.py        (wenn TST level: unit)
     - tests/contract/test_<slug>.py    (wenn TST level: contract)
     - tests/acceptance/test_<slug>.py  (wenn TST level: acceptance)
     Stub-Inhalt: pytest-Skelett mit TODO-Kommentar + Referenz auf TST-ID und Contract
     Bereits vorhandene Dateien werden NICHT überschrieben (Warnung)
  6. Gib TDD-Checkliste aus:
     "Tests angelegt – jetzt Code schreiben:"
     - tests/unit/test_<slug>.py       → TST-XXXX (rot, schlägt fehl)
     - tests/contract/test_<slug>.py   → TST-XXXX (rot, schlägt fehl)
     "Danach: sdd status SPEC-XXXX implemented"
  7. Schreibe Audit-Log-Eintrag (analog lifecycle.py)
```

### 3.3 Design Patterns

#### 3.3.1 State Pattern (Behavioral) — Lifecycle-Übergänge

**Anwendung:** Jeder Lifecycle-Status ist ein expliziter Zustand mit definierten
erlaubten Übergängen. `in-progress` ist ein neuer konkreter Zustand mit eigenem
Eintritts- (`approved`) und Ausgangszustand (`implemented`, `draft`).

**Begründung:** Verhindert illegale Übergänge (z. B. `draft → implemented`) ohne
komplexe if/else-Ketten. OCP: Neue Zustände werden als neue Klassen/Einträge ergänzt.

**Alternative:** Simple Dict-basierte Übergangsmatrix (wie aktuell in `validate.py`) –
bleibt vertretbar solange < 8 Zustände existieren.

#### 3.3.2 Command Pattern (Behavioral) — `sdd start`

**Anwendung:** `sdd start` kapselt alle Seiteneffekte (Status-Schreiben, Audit-Log,
Checklisten-Ausgabe) als eine unteilbare Operation. Kein Halbzustand bei Fehler.

**Begründung:** Wenn Schritt 3 (Status schreiben) gelingt, Schritt 6 (Audit-Log) aber
fehlschlägt, wäre der Zustand inkonsistent. Command-Kapselung erlaubt rollback-fähige
Ausführung.

---

## 4. Funktionale Anforderungen

### 4.1 Lifecycle-Erweiterung

**FR-01** `in-progress` wird als gültiger Status in allen JSON-Schemas ergänzt
(`spec-schema.json`, `contract-schema.json`).

**FR-02** `validate.py` erweitert die erlaubten Übergänge:
- Vorwärts: `approved → in-progress → implemented`
- Rückwärts: `in-progress → draft` (mit `[WARN]`)
- Illegal (Error): `in-progress → approved`, `draft → in-progress`

**FR-03** Das Frontmatter-Feld `started_at: <ISO-Datum>` wird beim `start`-Aufruf
gesetzt und ist optional (Schema: `nullable`).

### 4.2 `sdd start`-Befehl

**FR-04** `sdd start SPEC-XXXX` ist ein neuer Click-Befehl in `main.py`,
implementiert in `lifecycle.py`.

**FR-05** Vorbedingung: `status == approved`. Bei Verletzung:
`[ERROR] SPEC-XXXX hat Status 'draft' – erst Execution Gate durchlaufen (sdd execute SPEC-XXXX)`

**FR-06** Ausgabe enthält immer die TDD-Reihenfolge:
```
[INFO] SPEC-XXXX → in-progress
Tests zuerst schreiben:
  unit     → tests/unit/test_<slug>.py       (TST-XXXX)
  contract → tests/contract/test_<slug>.py   (TST-XXXX)
Dann Code implementieren. Danach: sdd status SPEC-XXXX implemented
```

**FR-07** `sdd start` erzeugt Test-Stub-Dateien für alle im Frontmatter verknüpften TST-IDs.
Stub-Format: pytest-Skelett mit `# TODO` + TST-ID-Referenz + Contract-Kurzbeschreibung.
Bereits vorhandene Dateien werden übersprungen (`[WARN] tests/unit/test_foo.py existiert – übersprungen`).

**FR-07b** Wenn keine Tests im Frontmatter verknüpft sind: `[WARN] Keine Tests verknüpft –
erstelle erst Tests mit 'sdd new test', dann erneut 'sdd start'`

### 4.3 Status-Check-Erweiterung

**FR-08** `sdd status-check` zeigt `in-progress`-Specs in eigener Sektion:
```
IN PROGRESS (1):
  SPEC-0019  TDD-Implementierungsphase   seit 2026-05-16  Tests: 3 verknüpft
```

**FR-09** 24-h-Warnung: Wenn `started_at` älter als 24 h und keine Testdatei unter
`tests/` für den SPEC-Slug existiert:
`[WARN] SPEC-XXXX ist seit >24h in-progress aber keine Testdatei gefunden`

---

## 5. Nicht-funktionale Anforderungen

| Attribut | Anforderung |
|---|---|
| Rückwärtskompatibilität | Bestehende Specs ohne `started_at`-Feld bleiben valide |
| Performance | `sdd start` läuft in < 1 s |
| Idempotenz | Mehrfaches `sdd start` auf `in-progress`-Spec gibt `[INFO] bereits in-progress` |
| Audit | Jede Status-Änderung landet in `.sdd/audit.log` (analog SPEC-0010) |

---

## 6. User Stories

| ID    | Als …       | möchte ich …                                                              | damit …                                                          |
|-------|-------------|---------------------------------------------------------------------------|------------------------------------------------------------------|
| US-01 | Entwickler  | nach dem Execution Gate `sdd start SPEC-XXXX` aufrufen                   | ich sofort weiß, welche Tests ich zuerst schreiben soll          |
| US-02 | Tech Lead   | in `sdd status-check` sehen welche Specs gerade in Entwicklung sind      | ich Fortschritt und Stagnation erkenne                           |
| US-03 | Entwickler  | eine Warnung bekommen wenn ich nach 24 h noch keine Tests angelegt habe  | ich nicht versehentlich Code-first entwickle                     |
| US-04 | Entwickler  | von `in-progress` zurück zu `draft` wechseln können                      | ich bei grundlegenden Designproblemen neu planen kann            |

---

## 7. Contracts

| Contract-ID | Typ      | Was wird garantiert?                                                                        |
|-------------|----------|---------------------------------------------------------------------------------------------|
| CON-0060    | behavior | Gherkin: `sdd start` – Vorbedingungen, Statusübergang, TDD-Checklisten-Ausgabe             |
| CON-0061    | data     | JSON Schema: `started_at`-Feld im Spec-Frontmatter; `in-progress` als gültiger Statuswert  |
| CON-0062    | behavior | Gherkin: `sdd status-check` – `in-progress`-Sektion + 24-h-Warnung                        |

---

## 8. Tests

| Test-ID  | Level      | Was prüft der Test?                                                                              |
|----------|------------|--------------------------------------------------------------------------------------------------|
| TST-0069 | unit       | `lifecycle.py`: start() setzt Status + started_at; Idempotenz; illegale Übergänge → Exception   |
| TST-0070 | contract   | Schema-Validierung: `in-progress` in spec-schema.json; `started_at` optional + nullable         |
| TST-0071 | acceptance | Gherkin aus CON-0060: `sdd start` auf approved Spec → Checkliste + Audit-Log-Eintrag            |

---

## 9. Implementierungsreihenfolge

```
Phase A: Schema-Erweiterung
  └─ spec-schema.json: in-progress als gültiger status-Wert
  └─ spec-schema.json: started_at (optional, nullable, ISO-Datum)

Phase B: validate.py – Lifecycle-Regeln
  └─ Übergangsmatrix erweitern: approved → in-progress → implemented
  └─ Rücksprung in-progress → draft als WARN (kein Error)
  └─ Illegale Übergänge als ERROR

Phase C: lifecycle.py – start()
  └─ start(spec_id) Funktion: Vorbedingung, Statusschreiben, started_at, Audit-Log
  └─ Checklisten-Generierung aus verknüpften Test-IDs

Phase D: main.py – sdd start Command
  └─ Click-Command: sdd start SPEC-XXXX
  └─ Rich-Output: TDD-Checkliste

Phase E: status-check Erweiterung
  └─ in-progress-Sektion in sdd status-check
  └─ 24-h-Warnung (Datei-Existenzprüfung unter tests/)

Phase F: Contracts + Tests
  └─ CON-0060, CON-0061, CON-0062
  └─ TST-0069, TST-0070, TST-0071
```

---

## 10. Offene Fragen

- [x] Soll `sdd start` automatisch Test-Stub-Dateien anlegen (analog `sdd new test`)?
      → Ja: Stubs werden erzeugt (FR-07); vorhandene Dateien werden nicht überschrieben
- [ ] Brauchen Contracts ebenfalls `in-progress`?
      → Nein: Contracts sind fertig bevor `sdd start` aufgerufen wird
- [ ] Soll `/sdd-status` (SPEC-0018) die neue `in-progress`-Sektion direkt aufgreifen?
      → Ja, als natürliche Erweiterung; SPEC-0018 hängt von SPEC-0019 ab

---

## 11. Änderungshistorie

| Datum      | Version | Autor | Änderung            |
|------------|---------|-------|---------------------|
| 2026-05-16 | 0.1.0   | Boris | Initiale Erstellung |
