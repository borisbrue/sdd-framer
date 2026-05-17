---
id: TST-0011
project: ""
title: "AGENTS.md Struktur-Validierung"
level: unit
spec: SPEC-0004
contract: CON-0011
status: planned
framework: "pytest"
artifact: "tests/unit/test_agents_md_validation.py"
tags: ["agents-md", "validation", "dark-factory"]
---

# Test: AGENTS.md Struktur-Validierung

> **Level:** unit · **Spec:** SPEC-0004 · **Contract:** CON-0011 · **Status:** planned

## Was wird geprüft?

Die Vollständigkeitsprüfung einer `AGENTS.md`-Datei gemäß CON-0011:
- Alle 8 Pflicht-Sektionen vorhanden (G-02)
- Warnung bei reinen Placeholder-Sektionen (G-03)
- `sdd new agents-md` erzeugt valides Skeleton (G-05)
- Bestehende Datei wird nicht überschrieben (G-05)

## Vorbedingungen

- `sdd-cli` installiert
- `pytest` mit `tmp_path`-Fixture

## Ablauf

### TC-01: Vollständiges AGENTS.md besteht Validierung

1. Erstelle AGENTS.md mit allen 8 Pflicht-Sektionen und echtem Inhalt
2. Führe Validierungsfunktion aus
3. Prüfe: keine Fehler, keine Warnungen

### TC-02: Fehlende Sektion → Warnung/Fehler

1. Erstelle AGENTS.md ohne `## Architektur`
2. Prüfe: Validierung gibt mindestens 1 Issue zurück
3. Prüfe: Issue referenziert die fehlende Sektion

### TC-03: Placeholder-Sektion → Warnung

1. Erstelle AGENTS.md mit `## Architektur\n\n<!-- ... -->\n`
2. Prüfe: Warnung (kein Fehler) wegen unvollständiger Sektion

### TC-04: sdd new agents-md erzeugt valides Skeleton

1. Rufe `sdd new agents-md` in einem temporären SDD-Projekt auf
2. Prüfe: `AGENTS.md` existiert im Projekt-Root
3. Prüfe: Alle 8 Pflicht-Sektionen im generierten Skeleton vorhanden

### TC-05: Kein Überschreiben bestehender Datei

1. Lege `AGENTS.md` manuell an
2. Rufe `sdd new agents-md` erneut auf
3. Prüfe: bestehende Datei unverändert, Warnung ausgegeben

## Erwartetes Ergebnis

Alle 5 Test-Cases bestehen ohne Dateisystem-Seiteneffekte außerhalb von `tmp_path`.

## Negativfälle / Edge Cases

- Leere `AGENTS.md` → alle 8 Sektionen fehlen → 8 Issues
- `AGENTS.md` nur mit H1 (`# AGENTS.md`) → alle H2-Sektionen fehlen

## Verknüpfung mit Contract

Dieser Test prüft konkret folgende Punkte aus CON-0011:

- [ ] G-02: Alle 8 Pflicht-Sektionen (TC-01, TC-02)
- [ ] G-03: Placeholder-Erkennung → Warnung (TC-03)
- [ ] G-05: sdd new agents-md Skeleton + Kein-Überschreiben (TC-04, TC-05)
- [ ] INV-01: Genau eine AGENTS.md im Root (TC-04)

## Hinweise zur Implementierung

Die Validierungslogik für AGENTS.md kann in `validate.py` als separate
Funktion `_check_agents_md(config, report)` eingebaut werden.
Pflicht-Sektionen als Konstante definieren:

```python
AGENTS_MD_REQUIRED_SECTIONS = [
    "## Service-Zweck",
    "## Architektur",
    "## Verzeichnisstruktur",
    "## Externe Abhängigkeiten",
    "## Build- und Start-Befehle",
    "## Linting- und Formatierungsregeln",
    "## Konventionen",
    "## SDD-Kontext",
]
```
