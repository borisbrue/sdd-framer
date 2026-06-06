<!-- skill: sdd-review | version: 0.2.0 | sdd-blueprint: true | updated: 2026-05-30 -->

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
und gehe direkt zu Schritt 5b.

## Schritt 2: SOLID-Analyse ausführen
```bash
sdd solid-check $ID
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
```bash
sdd pattern-suggest $ID
```
Zeige jeden Vorschlag mit:
- Pattern-Name + Kategorie (Behavioral / Structural / Creational)
- Warum hier passend (konkret auf das Artefakt bezogen)
- Alternative (was stattdessen möglich wäre + Ablehnungsgrund)
- Refactoring-Guru-Link

Frage für jeden Vorschlag: "Annehmen? (ja/nein/überspringen)"

Bei "ja":
```bash
sdd pattern accept $ID <PatternName> --reason "<Begründung>"
```

Bei "nein": frage nach Ablehnungsgrund, dann:
```bash
sdd pattern reject $ID <PatternName> --reason "<Grund>"
```

## Schritt 4: Regression-Check

[WARN] Falls `sdd regression-check` nicht verfügbar ist: Schritt überspringen und
`[WARN] sdd regression-check nicht verfügbar` ausgeben.

```bash
sdd regression-check $ID
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

## Schritt 5: Contract-Review (nur für CON-XXXX)

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

Frage ob Contract-Status auf `approved` gesetzt werden soll:
```bash
sdd contract approve CON-XXXX
```

## Schritt 5b: Test-Review (nur für TST-XXXX)

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
sdd regression-check <SPEC-ID>
```
Zeige das Ergebnis wie in Schritt 4 beschrieben. Bei `error`-Severity: stoppen und Konflikt
melden. Bei `warning`/`info` oder 0 Befunden: Gate-Phase `regression-ok` wird automatisch
durch den CLI-Befehl markiert — kein manueller Schritt nötig.

## Schritt 6: Zusammenfassung
```
Review abgeschlossen: SPEC-XXXX / CON-XXXX / TST-XXXX
- SOLID: 1 Warnung (ISP), 0 Violations
- Patterns: Strategy (angenommen), Decorator (abgelehnt)
- Nächster Schritt: sdd spec approve SPEC-XXXX (wenn bereit)
```
