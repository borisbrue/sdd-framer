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

Zeige das Ergebnis:
- Bei `error`-Severity: "⚠ Regression-Konflikt gefunden: CON-XXXX vs. CON-YYYY"
  Frage: "Weiter trotzdem? (ja/nein)" — warte auf explizite Nutzerentscheidung.
  Bei "nein": abbrechen.
- Bei `warning`-Severity: "⚠ Möglicher Konflikt (warning): ... – bitte prüfen"
  → Review-Flow fährt automatisch fort.
- Bei 0 Konflikten: "✓ Kein Regressionsrisiko gefunden"

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

## Schritt 6: Zusammenfassung
```
Review abgeschlossen: SPEC-XXXX / CON-XXXX / TST-XXXX
- SOLID: 1 Warnung (ISP), 0 Violations
- Patterns: Strategy (angenommen), Decorator (abgelehnt)
- Nächster Schritt: sdd spec approve SPEC-XXXX (wenn bereit)
```
