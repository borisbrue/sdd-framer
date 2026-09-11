<!-- skill: sdd-config | version: 0.1.0 | sdd-blueprint: true | updated: 2026-05-19 -->

# /sdd-config – Geführte SDD-Konfiguration

## Aufgabe

Lies die aktuelle `config.yaml`, erkenne Probleme, schlage Änderungen vor und schreibe
sie nach **expliziter Nutzerbestätigung**. Kein Schreiben ohne "ja" / "ok" / "speichern".

⚠️ KRITISCH: `.sdd/holdout/` wird NIEMALS gelesen. Dieses Verbot gilt auch für diesen Skill.

## Schritt 1: Config laden und prüfen

1. Prüfe ob `.sdd/config.yaml` existiert.
   Falls nicht: "Kein SDD-Projekt gefunden. Führe `sdd init` aus." und abbrechen.
2. Lese `.sdd/config.yaml` vollständig.
3. Führe aus: `sdd config validate`
4. Zeige strukturierte Übersicht aller Sections (project, llm inkl. `llm.roles`, docker, evaluator, orchestrator).
5. Hebe Probleme hervor:
   - `llm.roles`: Parameter, die der Provider ignoriert, und gleiches Modell für Reviewer und Implementierer
   - `max_parallel_containers < 1`
   - `registry.url` gesetzt ohne `registry.auth_env`
   - Fehlende Pflichtfelder
   - Platzhalter-Beschreibung (`<PROJECT_DESCRIPTION>`)

## Schritt 2: Geführter Dialog

Für jedes erkannte Problem:
- Beschreibe das Problem verständlich (kein YAML-Jargon)
- Schlage eine konkrete Korrektur vor als Diff-Vorschlag
- ⚠️ Schlage NIEMALS einen Klartext-API-Key vor — nur Env-Var-Namen wie `ANTHROPIC_API_KEY`
- Frage ob weitere Änderungen gewünscht sind

## Schritt 3: Schreiben nach Bestätigung

Erst wenn der Nutzer explizit bestätigt ("ja" / "ok" / "speichern" / "write"):
1. Schreibe Änderungen via `sdd config set <key>=<value>` (atomar)
2. Führe danach aus: `sdd config validate`
3. Zeige Validierungsergebnis

Falls der Nutzer "nein" / "abbrechen" antwortet: `config.yaml` bleibt unverändert.

## Sicherheitsregeln (unverletzlich)

- **Kein Schreiben ohne explizite Bestätigung** (INV-01)
- **Kein Lesen von `.sdd/holdout/`** (INV-02)
- **Kein Klartext-API-Key** in Vorschlägen oder Writes — nur Env-Var-Namen (INV-04)
- **Kein Schreiben wenn `config.yaml` fehlt** — erst `sdd init` (INV-03)

## Hilfreiche Befehle

```bash
sdd config show              # Aktuelle Config anzeigen
sdd config show --section llm  # Nur LLM-Section
sdd config set <key>=<value> # Einzelnen Wert setzen
sdd config validate          # Vollständige Validierung
sdd config test-llm          # LLM-Provider testen
sdd config wizard            # Interaktiver Wizard
sdd config wizard --section llm  # Nur LLM-Section konfigurieren
```

## Beispiel-Workflow

```
Nutzer: /sdd-config
→ Skill liest config.yaml
→ Erkennt: llm.roles.reviewer nutzt dasselbe Modell wie llm.roles.implementer
→ Schlägt vor: reviewer auf claude-cli umstellen
→ Nutzer: "ja"
→ Schreibt: sdd config set llm.roles.reviewer.provider=claude-cli
→ Führt aus: sdd config validate → ✓
```
