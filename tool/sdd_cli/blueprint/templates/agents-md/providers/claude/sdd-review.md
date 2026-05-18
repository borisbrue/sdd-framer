<!-- skill: sdd-review | version: 0.1.0 | sdd-blueprint: true | updated: 2026-05-16 -->

# /sdd-review – SOLID-Analyse + Pattern-Vorschläge

## Aufgabe
Führe eine SOLID-Analyse und Pattern-Empfehlung für eine SPEC oder einen Contract durch.
`$ARGUMENTS` enthält die Artefakt-ID (SPEC-XXXX oder CON-XXXX) oder `--pending`.

## Schritt 1: Vorbedingung
Prüfe ob `.sdd/config.yaml` existiert. Falls nicht: Fehlermeldung und abbrechen.

**Bei `--pending`:**
Liste alle Contracts mit `status: draft` auf und frage welchen der Nutzer reviewen möchte.

**Bei leeren `$ARGUMENTS`:**
Frage: "Welche SPEC oder CON-ID soll reviewed werden?"

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

## Schritt 4: Contract-Review (nur für CON-XXXX)
Lese den Contract + verknüpften SPEC.
Prüfe inhaltlich:
- Ist die Garantie messbar und testbar?
- Fehlen Randbedingungen (Timeouts, Fehlerfälle)?
- Ist der Contract atomar (eine Verantwortlichkeit)?

Frage ob Contract-Status auf `approved` gesetzt werden soll:
```bash
# Frontmatter status: draft → approved patchen
```

## Schritt 5: Zusammenfassung
```
Review abgeschlossen: SPEC-XXXX
- SOLID: 1 Warnung (ISP), 0 Violations
- Patterns: Strategy (angenommen), Decorator (abgelehnt)
- Nächster Schritt: sdd spec approve SPEC-XXXX (wenn bereit)
```
