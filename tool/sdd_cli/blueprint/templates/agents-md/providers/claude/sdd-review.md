<!-- skill: sdd-review | version: 0.6.0 | sdd-blueprint: true | updated: 2026-09-11 -->

# /sdd-review – Review-Kette bis zum Approve

## Aufgabe
Führe das Review für eine SPEC, einen Contract oder einen Test durch. Bei einer SPEC
bringst du sie bis `sdd spec approve`.
`$ARGUMENTS` enthält die Artefakt-ID (SPEC-XXXX, CON-XXXX oder TST-XXXX) oder `--pending`.

## Die Gate-Kette – zuerst lesen

`sdd spec approve` prüft das Execution Gate (CON-0025). Jede Phase setzt die vorherige
voraus. Zwei Phasen sind Zustände, alle anderen schließt genau ein Befehl ab:

| Phase | abgeschlossen durch |
|---|---|
| `spec-draft` | Zustand: Spec-Datei mit `id`, `title`, `status`, `owner`, `version` |
| `spec-review` | `sdd spec review SPEC-XXXX` (Schritt 2) |
| `contracts-proposed` | `sdd contract propose SPEC-XXXX CON-… CON-…` (Schritt 4) |
| `contracts-draft` | Zustand: jeder vorgeschlagene Contract existiert samt `artifact`-Datei |
| `contracts-review` | `sdd contract analyze SPEC-XXXX CON-… CON-…` (Schritt 4) |
| `tests-generated` | `sdd test generate SPEC-XXXX CON-… CON-…` (Schritt 5) |
| `regression-ok` | `sdd spec regression SPEC-XXXX` (Schritt 6) |
| `spec-approved`, `execute-unlocked` | `sdd spec approve SPEC-XXXX` (Schritt 7) |

Den Stand zeigt `.sdd/pipeline/SPEC-XXXX-gate.json` (`phase_history`). Ein manuell
per Edit-Tool gesetztes `status: approved` im Contract sieht das Gate nicht.

Meldet ein Befehl `✗ Phase 'X' noch nicht abgeschlossen`: Der Befehl zur Phase X aus der
Tabelle fehlt. Hole ihn nach und wiederhole den Befehl. Nie das Gate umgehen.

Bis v0.5.0 kannte dieser Skill nur Schritt 2, 6 und 7; Approve scheiterte an den
Zwischenphasen, sobald das Gate sie verlangte.

## Schritt 1: Vorbedingung
Prüfe ob `.sdd/config.yaml` existiert. Falls nicht: Fehlermeldung und abbrechen.

**Bei `--pending`:**
Liste alle Contracts mit `status: draft` auf und frage welchen der Nutzer reviewen möchte.

**Bei leeren `$ARGUMENTS`:**
Frage: "Welche SPEC, CON-ID oder TST-ID soll reviewed werden?"

**Bei CON-XXXX:** Schritt 4b für diesen Contract, dann Schritt 8. Die Gate-Phasen laufen
über die Spec; nenne am Ende `/sdd-review SPEC-XXXX` als nächsten Schritt.

**Bei TST-XXXX:** direkt zu Schritt 5c, dann Schritt 8.

## Schritt 2: Spec-Review – SOLID-Analyse + Pattern-Vorschläge

```bash
sdd spec review $ID
```

Der Befehl schließt die Phase `spec-review` ab. SOLID-Analyse und Pattern-Vorschläge
laufen darin, wenn `solid_gate.enabled` bzw. `pattern_suggestions.enabled` in
`.sdd/config.yaml` gesetzt sind. Sind sie deaktiviert und du willst die Analyse
trotzdem: `sdd review spec $ID` (beratend, ohne Gate-Wirkung).

Zeige das SOLID-Ergebnis übersichtlich:

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

Bei SOLID-Verletzungen: erkläre die Konsequenz für Implementierung und Wartbarkeit.

Zeige jeden Pattern-Vorschlag mit:
- Pattern-Name + Kategorie (Behavioral / Structural / Creational)
- Warum hier passend (konkret auf das Artefakt bezogen)
- Alternative (was stattdessen möglich wäre + Ablehnungsgrund)
- Refactoring-Guru-Link

Die Vorschläge beziehen seit SPEC-0048 den projektweiten Pattern-Katalog
(`.sdd/patterns/_catalog.json`) ein: bereits akzeptierte Patterns werden bei
thematischer Nähe referenziert statt erneut vorgeschlagen.

Gibt es keine Vorschläge ("Keine Pattern-Vorschläge generiert"): weiter zu Schritt 4.

## Schritt 3: Pattern-Entscheidungen festhalten

Frage für jeden Vorschlag: "Annehmen? (ja/nein/überspringen)"

Bei "ja":
```bash
sdd review pattern accept $ID <PatternName> --reason "<Begründung>" --url "<RefactoringGuruURL>"
```

Bei "nein": frage nach dem Ablehnungsgrund, dann:
```bash
sdd review pattern reject $ID <PatternName> --reason "<Grund>"
```

Bei "überspringen": keine Aktion, weder Register noch Katalog werden verändert.

Festgehaltene Entscheidungen: `sdd review pattern list $ID`.

## Schritt 4: Contracts – vorschlagen, reviewen, analysieren

### 4a: Contracts ermitteln oder erstellen

```bash
grep "^contracts:" <spec-file>
```

**Keine Contracts verknüpft (`contracts: []`):** erstelle alle notwendigen Contracts
**automatisch** anhand der FRs und der Contracts-Tabelle der Spec. Leite den Nutzer
nicht weiter.

- Welche Contract-Typen werden benötigt?
  - `api` → wenn FRs REST-Endpunkte beschreiben
  - `behavior` → wenn Gherkin-Szenarien vorhanden (Abschnitt 6/7)
  - `data` → wenn Datenmodelle spezifiziert werden
  - `performance` → wenn NFRs messbare Latenzen/SLOs enthalten
- Nächste freie CON-ID ermitteln (analog zu sdd-new)
- Contract-Dokument **und** Artifact-Datei (OpenAPI YAML / `.feature` / Schema) schreiben.
  Die Artifact-Datei ist Pflicht: die Phase `contracts-draft` gilt erst, wenn jede
  im Frontmatter unter `artifact:` genannte Datei existiert.
- CON-IDs im Spec-Frontmatter eintragen

Dann Phase `contracts-proposed` abschließen, mit **allen** Contracts der Spec:
```bash
sdd contract propose $ID CON-XXXX CON-YYYY
```
Der Befehl meldet `Gate-Phase contracts-draft erfüllt`, wenn alle Dokumente und
Artifact-Dateien da sind. Fehlt die Meldung: fehlende Artifact-Datei anlegen, Befehl
wiederholen.

### 4b: Inhaltlicher Review je Contract

Für jeden Contract mit `status: draft` (bei CON-XXXX direkt: nur dieser):

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

Ergänzend das LLM-Review, beratend:
```bash
sdd review contract CON-XXXX
```

Falls Anpassungen nötig: liste sie konkret auf und warte auf Bestätigung, bevor
die Contract-Datei geändert wird.

Frage, ob der Contract-Status auf `approved` gesetzt werden soll.
Bei "ja": setze `status: approved` im Frontmatter (Edit-Tool). Das dokumentiert die
Entscheidung; die Gate-Phase kommt erst mit 4c.
Bei "nein": nenne den Contract als offen. Schritt 7 bleibt aus, solange ein Contract
der Spec `draft` ist.

### 4c: Konfliktanalyse – Phase `contracts-review`

```bash
sdd contract analyze $ID CON-XXXX CON-YYYY
```

Meldet der Befehl Konflikte: zeige sie mit Severity. Offene Konflikte blockieren die
nächste Phase (`tests-generated`). Auflösen oder bewusst bestätigen:
```bash
sdd conflict list $ID
sdd conflict resolve $ID <CONFLICT-ID> --action "<Auflösung>"
sdd conflict acknowledge $ID <CONFLICT-ID> --reason "<Grund>"
```

## Schritt 5: Tests – Phase `tests-generated`

### 5a: Testrümpfe erzeugen oder abgleichen

```bash
sdd test generate $ID CON-XXXX CON-YYYY
```

Je Contract entsteht eine Testdatei mit einem Rumpf pro Szenario/Endpunkt, oder eine
vorhandene Datei wird um fehlende Rümpfe ergänzt. `=` heißt unverändert; der Grund
steht dabei (etwa: die Datei bindet das Feature per `scenarios()`). Eine `⚠`-Zeile
nennt Contracts ohne erkanntes Szenario.

### 5b: TST-Dokumente und Verknüpfungen

Für jeden Contract:
- TST-Dokument in `.sdd/tests/<level>/` mit `artifact:` auf die Testdatei
- FR-Test-Map (`fr_test_map`) im Spec-Frontmatter eintragen
- `tests:`-Liste im Contract-Frontmatter mit TST-IDs befüllen
- `tests:`-Liste im Spec-Frontmatter befüllen — Schritt 7 verlangt sie

### 5c: Test-Review (nur für TST-XXXX)

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

Falls Anpassungen nötig: liste sie konkret auf. Warte auf Bestätigung, bevor die
Test-Datei geändert wird.

**Führe IMMER den Regression-Check auf der übergeordneten Spec durch** (SPEC-ID aus
`spec:`-Frontmatter des Tests), wie in Schritt 6 beschrieben.

## Schritt 6: Regression-Check – Phase `regression-ok`

[WARN] Falls `sdd spec regression` nicht verfügbar ist (älteres sdd): Schritt überspringen und
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
Bei nur `warning`/`info`: weiter.
Bei 0 Befunden in beiden Stufen: "✓ Kein Regressionsrisiko gefunden"

**Ohne LLM-Zugang** (kein `claude` im PATH, kein API-Key) wird Stufe 2 übersprungen,
und der Befehl markiert `regression-ok` nicht. Prüfe die semantischen Überschneidungen
dann selbst: lies die FRs der fachlich nächsten Specs und vergleiche sie mit denen von
$ID. Erst danach:
```bash
sdd spec regression $ID --allow-skipped-llm
```

## Schritt 7: Approve – Phasen `spec-approved` und `execute-unlocked`

Nur wenn kein Contract der Spec mehr `draft` ist:
```bash
sdd spec approve $ID
```

Der Befehl verlangt `contracts:` und `tests:` im Spec-Frontmatter und lässt die
Compliance-Kette laufen (FR-Abdeckung, Task-Status). Bei `✗`: die Meldung nennt, was
fehlt; hole es nach (Schritt 4 oder 5) und wiederhole den Befehl.

Gibt es noch Draft-Contracts: nenne sie explizit, `sdd spec approve` bleibt aus.

## Schritt 8: Zusammenfassung
```
Review abgeschlossen: SPEC-XXXX / CON-XXXX / TST-XXXX
- Gate: spec-review ✓ · contracts-proposed ✓ · contracts-draft ✓ · contracts-review ✓
        tests-generated ✓ · regression-ok ✓ · spec-approved ✓
- SOLID: 1 Warnung (ISP), 0 Violations
- Patterns: Strategy (angenommen), Decorator (abgelehnt)
- Contracts: CON-XXXX (api) ✓ approved · CON-YYYY (behavior) ✓ approved
- Nächster Schritt: /sdd-implement SPEC-XXXX
```

Bei CON-XXXX oder TST-XXXX endet der Skill hier; nächster Schritt ist
`/sdd-review SPEC-XXXX`, damit die Gate-Kette der Spec weiterläuft.
