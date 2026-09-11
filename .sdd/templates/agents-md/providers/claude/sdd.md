<!-- skill: sdd | version: 0.1.0 | sdd-blueprint: true | updated: 2026-05-16 -->

# /sdd – SDD Projektübersicht & Skill-Hilfe

## Aufgabe
Zeige eine kompakte Übersicht des SDD-Projekts: alle Specs mit Status,
verfügbare Skills und offene Blockaden.

> **Autonomie-Setup (SPEC-0051):** `sdd init` installiert den PreToolUse-Guardrail-Hook
> (`.claude/hooks/autonomous-guardrail.sh`) automatisch. Für vollautonome Läufe (Spec → PR
> ohne Permission-Prompts) `sdd init --autonomous` nutzen – das setzt
> `permissions.defaultMode: bypassPermissions` nur lokal in `.claude/settings.local.json`
> (gitignored, nicht für Clones erzwungen). Der Guardrail blockt katastrophale Kommandos
> auch unter Bypass.

## Schritt 1: Projekt prüfen
- Prüfe ob `.sdd/config.yaml` existiert.
  Falls nicht: "Kein SDD-Projekt gefunden. Führe zuerst 'sdd init' aus." und abbrechen.
- Lese `.sdd/config.yaml` → Projektname ausgeben.

## Schritt 2: Spec-Status-Tabelle
Lese alle `.md`-Dateien in `.sdd/specs/` (nur Dateien mit YAML-Frontmatter, kein README).
Extrahiere je Datei: `id`, `title` (max. 40 Zeichen), `status`, Anzahl `contracts`, Anzahl `tests`.

Gib eine Tabelle aus:

```
## SDD Projektübersicht – <Projektname>

| Spec      | Titel                        | Status      | Contracts | Tests |
|-----------|------------------------------|-------------|-----------|-------|
| SPEC-0001 | User Login                   | implemented |         3 |     4 |
| SPEC-0017 | VS Code Full Flow            | draft       |         3 |     3 |
```

Status-Farben (Markdown-Fettschrift für wichtige): **draft** = offen, implemented = fertig.

## Schritt 3: Verfügbare Skills
```
**Verfügbare /sdd-Skills:**
- /sdd           – Projektübersicht (dieser Befehl)
- /sdd-new       – Spec, Contract, Test oder ADR erstellen
- /sdd-review    – SOLID-Analyse + Contract-Review
- /sdd-implement – TDD-Implementierungsphase starten
- /sdd-holdout   – Holdout-Szenarien generieren + evaluieren
- /sdd-hotfix    – Schlanker Hotfix-Flow
- /sdd-status    – Lifecycle-Status und Blockaden
- /sdd-validate  – Projekt validieren + Fehler erklären
- /sdd-config    – Geführte SDD-Konfiguration
```

## Schritt 4: Offene Punkte
Zähle und zeige:
- Specs mit `status: draft` → Anzahl
- Specs mit `status: in-progress` → Anzahl + Namen
- Specs mit `status: approved` aber ohne alle Contracts `approved` → Warnung
- Führe `sdd validate 2>&1 | tail -3` aus und zeige die Zusammenfassung

Beispiel-Ausgabe:
```
**Offene Punkte:**
- 4 Specs in draft
- 1 Spec in-progress: SPEC-0019
- 0 Validierungsfehler
```
