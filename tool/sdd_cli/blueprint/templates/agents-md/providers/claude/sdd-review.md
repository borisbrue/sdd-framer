<!-- skill: sdd-review | version: 0.4.0 | sdd-blueprint: true | updated: 2026-06-09 -->

# /sdd-review – SOLID-Analyse + Pattern-Vorschläge

## Aufgabe
Führe eine SOLID-Analyse und Pattern-Empfehlung für eine SPEC oder einen Contract durch.
`$ARGUMENTS` enthält die Artefakt-ID (SPEC-XXXX oder CON-XXXX) oder `--pending`.

## Schritt 1: Vorbedingung
Prüfe ob `.sdd/config.yaml` existiert. Falls nicht: Fehlermeldung und abbrechen.

**Bei `--pending`:**
Liste alle Contracts mit `status: draft` auf und frage welchen der Nutzer reviewen möchte.

**Bei leeren `$ARGUMENTS`:**
Frage: "Welche SPEC, CON-ID oder TST-ID soll reviewed werden?"

**Bei TST-XXXX:** überspringe Schritte 2–4 (SOLID/Pattern/Regression gelten nicht für Tests)
und gehe direkt zu Schritt 5c.

## Schritt 2: SOLID-Analyse ausführen
```bash
sdd spec solid $ID
```
Zeige das Ergebnis übersichtlich:

```
── SOLID-Analyse: SPEC-XXXX ────────────────────────────
  ✓ S – Single Responsibility: klar abgegrenzt
  ✓ O – Open/Closed: Erweiterungspunkte beschrieben
  ✓ L – Liskov Substitution: keine Subtypen-Konflikte
  ! I – Interface Segregation [WARN]
    → Abschnitt 6.3: Zu viele optionale Flags in einem Command.
      Erwäge separate Subcommands.
  ✓ D – Dependency Inversion: Abstraktion korrekt
```

Bei SOLID-Verletzungen: erkläre konsequenz für Implementierung und Maintainability.

## Schritt 3: Pattern-Vorschläge

Die Vorschläge entstehen als Teil von `sdd review spec` (Schritt 2) — einen
eigenen Befehl dafür gibt es seit SPEC-0044 nicht mehr.

```bash
sdd review spec $ID
```

Zeige jeden Vorschlag mit:
- Pattern-Name + Kategorie (Behavioral / Structural / Creational)
- Warum hier passend (konkret auf das Artefakt bezogen)
- Alternative (was stattdessen möglich wäre + Ablehnungsgrund)
- Refactoring-Guru-Link

Besprich jeden Vorschlag mit dem Nutzer und halte die Entscheidung im
Contract-Text fest — einen Befehl, der sie maschinell speichert, gibt es
derzeit nicht.

## Schritt 4: Regression-Check

[WARN] Falls `sdd spec regression` nicht verfügbar ist: Schritt überspringen und
`[WARN] sdd spec regression nicht verfügbar` ausgeben.

```bash
sdd spec regression $ID
```

Zeige Stufe-1- und Stufe-2-Befunde **getrennt** mit Präfix `[rule]` bzw. `[llm]`:

```
── Regression-Check: SPEC-XXXX ─────────────────────────
  Stufe 1 – Regelbasiert:
    [rule] error   CON-0111 vs. CON-0001 – Endpoint-Konflikt: POST /api/specs
    [rule] ✓ keine weiteren Regelkonflikte

  Stufe 2 – LLM-Semantik:
    [llm]  warning SPEC-0005 §FR-03 – semantische Überschneidung mit FR-02
                   "Beide Specs beschreiben Analyse-Session-Tracking"
    [llm]  ✓ keine weiteren inhaltlichen Konflikte
```

Bei `error`-Severity (egal ob `[rule]` oder `[llm]`):
  "⚠ Regression-Konflikt gefunden" + Details — Frage: "Weiter trotzdem? (ja/nein)"
  Bei "nein": abbrechen.
Bei nur `warning`/`info`: Review-Flow fährt automatisch fort.
Bei 0 Befunden in beiden Stufen: "✓ Kein Regressionsrisiko gefunden"
Falls LLM nicht erreichbar: `[llm] ⚠ LLM-Check übersprungen (kein API-Zugang)` — Stufe-1-Ergebnisse werden normal angezeigt.

## Schritt 5: Contract-Review

### 5a: Bei SPEC-XXXX — Contracts prüfen und reviewen

Prüfe zunächst ob die Spec überhaupt Contracts hat:
```bash
grep "^contracts:" <spec-file>
```

**Keine Contracts verknüpft (`contracts: []`):** → weiter zu Schritt 7
(Contracts werden dort automatisch erstellt und reviewed).

**Contracts vorhanden — ermittle Draft-Contracts:**
```bash
grep -rl "spec: SPEC-XXXX" .sdd/contracts/ | xargs grep -l "^status: draft"
```

Gibt es Draft-Contracts: Führe Schritt 5b für jeden Contract sequenziell durch.
Danach, wenn alle Contracts der Spec `approved` sind:
```bash
sdd spec approve SPEC-XXXX
```

Gibt es keine Draft-Contracts (alle bereits `approved`): weiter zu Schritt 6.

### 5b: Inhaltlicher Review eines einzelnen Contracts (CON-XXXX direkt oder aus 5a)

Lade als Kontext:
1. Den Contract selbst
2. Das verknüpfte Spec (aus `spec:`-Frontmatter des Contracts)
3. Alle anderen Contracts desselben Specs:
   ```bash
   grep -rl "spec: $(grep '^spec:' <contract-file> | awk '{print $2}')" .sdd/contracts/
   ```

Prüfe inhaltlich:
- Ist die Garantie messbar und testbar?
- Fehlen Randbedingungen (Timeouts, Fehlerfälle)?
- Ist der Contract atomar (eine Verantwortlichkeit)?
- Gibt es Überschneidungen oder Widersprüche mit den anderen Contracts desselben Specs?

Falls Anpassungen nötig: liste sie konkret auf und warte auf Bestätigung bevor
die Contract-Datei geändert wird.

Frage ob Contract-Status auf `approved` gesetzt werden soll.
Bei "ja": setze `status: approved` im Frontmatter der Contract-Datei (Edit-Tool).
Bei "nein": markiere den Contract als übersprungen — `sdd spec approve` wird
am Ende nur aufgerufen wenn wirklich alle Contracts der Spec `approved` sind.

Nach dem letzten Contract (bei CON-XXXX direkt oder am Ende von 5a):
Prüfe ob alle Contracts der Spec jetzt `approved` sind:
```bash
grep -rl "spec: SPEC-XXXX" .sdd/contracts/ | xargs grep -l "^status: draft"
```
Gibt es keine Draft-Contracts mehr:
```bash
sdd spec approve SPEC-XXXX
```
Gibt es noch Draft-Contracts: nenne sie explizit — `sdd spec approve` bleibt aus.

## Schritt 5c: Test-Review (nur für TST-XXXX)

Lade als Kontext:
1. Die Test-Datei selbst (aus TST `artifact:`-Frontmatter)
2. Den verknüpften Contract (aus `contract:`-Frontmatter des Tests)
3. Das verknüpfte Spec

Prüfe inhaltlich:
- Deckt der Test den Contract vollständig ab (Happy Path + mindestens 1 Fehlerfall)?
- Sind alle Contract-Invarianten als eigene Test-Cases abgebildet?
- Ist jeder Test unabhängig (kein versteckter State zwischen Tests)?
- Sind die Assertions konkret und nicht trivial (kein `assert True`)?
- Sind die Testdaten realistisch und repräsentativ?

Falls Anpassungen nötig: liste sie konkret auf. Warte auf Bestätigung bevor die Test-Datei
geändert wird.

**Führe IMMER — unabhängig davon ob Test-Anpassungen nötig waren — den Regression-Check
auf der übergeordneten Spec durch** (SPEC-ID aus `spec:`-Frontmatter des Tests):
```bash
sdd spec regression <SPEC-ID>
```
Zeige das Ergebnis wie in Schritt 4 beschrieben. Bei `error`-Severity: stoppen und Konflikt
melden. Bei `warning`/`info` oder 0 Befunden: Gate-Phase `regression-ok` wird automatisch
durch den CLI-Befehl markiert — kein manueller Schritt nötig.

## Schritt 6: Zusammenfassung
```
Review abgeschlossen: SPEC-XXXX / CON-XXXX / TST-XXXX
- SOLID: 1 Warnung (ISP), 0 Violations
- Patterns: Strategy (angenommen), Decorator (abgelehnt)
- Nächster Schritt: siehe Schritt 7 (bei SPEC) oder abgeschlossen
```

## Schritt 7: Post-Spec-Flow (nur bei SPEC-XXXX)

Dieser Schritt greift **nur wenn $ARGUMENTS eine SPEC-ID ist**.
Bei CON-XXXX oder TST-XXXX: Skill endet nach Schritt 6.

### 7a: Contracts automatisch erstellen (wenn keine vorhanden)

Sind `contracts: []` im Spec-Frontmatter:

Leite den Nutzer **nicht** weiter — erstelle alle notwendigen Contracts
**automatisch** anhand der FRs und der Contracts-Tabelle aus der Spec:

- Welche Contract-Typen werden benötigt?
  - `api` → wenn FRs REST-Endpunkte beschreiben
  - `behavior` → wenn Gherkin-Szenarien vorhanden (Abschnitt 6/7)
  - `data` → wenn Datenmodelle spezifiziert werden
  - `performance` → wenn NFRs messbare Latenzen/SLOs enthalten
- Nächste freie CON-ID ermitteln (analog zu sdd-new)
- Contract-Dokument + Artifact-Datei (OpenAPI YAML / .feature / etc.) schreiben
- CON-IDs im Spec-Frontmatter eintragen

Sind bereits Contracts verknüpft (alle `approved`): direkt zu Schritt 7c.

### 7b: Contract-Reviews automatisch durchführen

Führe für jeden soeben erstellten Contract **ohne Rückfrage** durch:
1. `sdd spec solid CON-XXXX`
2. `sdd spec regression CON-XXXX`
3. Inhaltlichen Review (Prüffragen aus Schritt 5b) + Fixes direkt einarbeiten
4. `status: approved` setzen

### 7c: Ergebnisse präsentieren – gemeinsam besprechen

Zeige eine kompakte Zusammenfassung aller Contract-Reviews:

```
── Contract-Reviews abgeschlossen ───────────────────────
  CON-XXXX (api):      ✓ approved  [N Fixes]
  CON-XXXX (behavior): ✓ approved  [N Fixes]
  Fixes: [Liste der wichtigsten Änderungen]
```

**Warte auf Nutzer-Feedback.** Anpassungen an Contracts oder Spec
gemeinsam besprechen, bevor Tests erstellt werden.

### 7d: Tests automatisch anlegen (nach Bestätigung durch Nutzer)

Sobald der Nutzer bestätigt (ja / ok / weiter / passt):

Erstelle für jeden approved Contract **automatisch** alle notwendigen Tests:
- TST-Dokument in `.sdd/tests/<level>/`
- Testdatei in `tests/<level>/` (Sprache/Framework des Projekts)
- FR-Test-Map (`fr_test_map`) im Spec-Frontmatter eintragen
- `tests:`-Liste im Contract-Frontmatter mit TST-IDs befüllen

Danach Spec approven:
```bash
sdd spec approve SPEC-XXXX
```

**Nächster Schritt nach Schritt 7:** `/sdd-implement SPEC-XXXX`
