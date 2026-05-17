# AGENTS.md – SDD Blueprint

Kontext-Datei für KI-Agenten und automatisierte Tools. Wird von `sdd validate` auf Vollständigkeit geprüft.

## Service-Zweck

SDD Blueprint ist ein sprachneutrales Spec-Driven Development System. Es erzwingt Traceability zwischen Feature-Specs, Contracts und Tests und stellt sicher, dass kein Code ohne dokumentierte Anforderung und Contract existiert.

Bestandteile:
- **`sdd`-CLI** – Dokumente anlegen, validieren, Traceability erzeugen
- **Web API** – FastAPI-Wrapper um die CLI-Logik
- **VS Code Extension** – TreeView, Linting, Go-to-Definition (in Entwicklung)
- **Blueprint** – Das gesamte Repo dient als wiederverwendbares Grundgerüst (`sdd init` kopiert es)

## Architektur

```
Web UI / VS Code Extension
        │
        ▼
   FastAPI (web/)
        │
        ▼
  sdd_cli (tool/sdd_cli/)
        │
   ┌────┴────────────────┐
   │                     │
Filesystem           .sdd/
(specs/, contracts/,  config.yaml
 tests/, docs/)       schemas/
                       templates/
```

Die CLI ist der einzige Schreiber auf dem Filesystem. Web API und Extension delegieren alle Operationen an die CLI-Module. Keine Datenbank – alle Daten liegen als Markdown-Dateien mit YAML-Frontmatter vor.

## Verzeichnisstruktur

```
.sdd/               # Projektkonfiguration
  config.yaml       # Name, Präfixe, aktive Regeln
  schemas/          # JSON-Schemas für Frontmatter-Validierung
  templates/        # Jinja2-Templates für neue Dokumente
specs/              # SPEC-XXXX-*.md  – Feature-Anforderungen
contracts/
  api/              # CON-XXXX – OpenAPI-Contracts
  behavior/         # CON-XXXX – Gherkin-Contracts
  performance/      # CON-XXXX – SLO-Contracts
tests/
  unit/             # TST-XXXX – Unit-Tests
  contract/         # TST-XXXX – Contract-Konformitätstests
  acceptance/       # TST-XXXX – Acceptance-Tests
  performance/      # TST-XXXX – Performance-Tests
docs/
  adr/              # ADR-XXXX – Architecture Decision Records
  traceability.md   # Generiert von `sdd trace`
tool/
  sdd_cli/          # Python-Paket: CLI-Kern
web/                # FastAPI-App
vscode-extension/   # VS Code Extension (TypeScript)
```

## Externe Abhängigkeiten

| Paket | Zweck |
|---|---|
| `click` ≥ 8.1 | CLI-Framework |
| `pyyaml` ≥ 6.0 | YAML-Frontmatter-Parsing |
| `jsonschema` ≥ 4.21 | Frontmatter-Schemavalidierung |
| `rich` ≥ 13.7 | Terminal-Ausgabe (Tabellen, Farben) |
| `fastapi` ≥ 0.111 | Web-API-Framework |
| `uvicorn[standard]` ≥ 0.29 | ASGI-Server |
| `ruff` ≥ 0.4 | Linting + Formatting (dev) |
| `pytest` ≥ 8.0 | Tests (dev) |
| `httpx` ≥ 0.27 | HTTP-Client für API-Tests (dev) |

Keine Datenbank, kein externer Service – das System ist vollständig offline-fähig.

## Build- und Start-Befehle

```bash
# Abhängigkeiten installieren (uv empfohlen)
uv sync
# oder klassisch:
cd tool && pip install -e ".[dev]"

# CLI nutzen
sdd --help
sdd validate
sdd status

# Neue Dokumente anlegen
sdd new spec "Feature Name"
sdd new contract --spec SPEC-0001 --format openapi --title "API Titel"
sdd new test --spec SPEC-0001 --contract CON-0001 --level contract --title "Test Titel"
sdd new adr "Architekturentscheidung"

# Traceability-Matrix erzeugen
sdd trace

# Web API starten
cd web && uvicorn main:app --reload

# Tests ausführen
pytest
pytest tests/unit/
pytest tests/contract/
```

## Linting- und Formatierungsregeln

Tool: **ruff** (konfiguriert in `pyproject.toml`)

```bash
ruff check tool/          # Linting
ruff check tool/ --fix    # Auto-Fix
ruff format tool/         # Formatierung
```

Aktive Regelgruppen: `E`, `F`, `I` (isort), `UP` (pyupgrade), `B` (bugbear), `SIM` (simplify).  
Zeilenlänge: 100 Zeichen. `E501` (Zeilenlängen-Fehler) ist deaktiviert.  
Python-Zielversion: 3.10+.

Für die VS Code Extension gilt: TypeScript strict mode, ESLint mit Standard-Regeln.

## Konventionen

**Dokument-IDs** werden automatisch von der CLI vergeben – niemals manuell nummerieren.

**Dateinamen-Schema:**
- `SPEC-XXXX-kebab-case-titel.md`
- `CON-XXXX-kebab-case-titel.md`
- `TST-XXXX-kebab-case-titel.md`
- `ADR-XXXX-kebab-case-titel.md`

**Frontmatter:** Jedes Dokument hat YAML-Frontmatter. Das Schema liegt in `.sdd/schemas/`. `sdd validate` prüft Konformität.

**Referenzielle Integrität** (Invarianten):
1. Jede Spec referenziert ≥ 1 Contract.
2. Jeder Contract referenziert ≥ 1 Test.
3. Alle Referenzen zeigen auf existierende Dokumente.
4. Keine verwaisten Contracts oder Tests ohne Spec-Bezug.

**Commit-Stil:** Konventionelle Commits (`feat:`, `fix:`, `docs:`, `chore:`).  
**Sprache:** Deutsch in Kommentaren, Docs und Commit-Messages; Englisch im Code.

## SDD-Kontext

Dieses Repository *ist selbst* das Blueprint. Es dient zwei Zwecken gleichzeitig:

1. **Laufendes System** – Die CLI ist hier installierbar und voll funktionsfähig.
2. **Vorlage** – `sdd init --name "Neues Projekt"` kopiert die Struktur in ein anderes Verzeichnis.

Das Beispiel-Feature **"User Login"** (SPEC-0001 → CON-0001/2/3 → TST-0001/2/3/4, ADR-0001) zeigt, wie alle Bestandteile zusammenwirken. Beim Anpassen des Blueprints diese Beispieldateien ersetzen, nicht löschen.

In CI sollte `sdd validate --strict` als Pflicht-Gate laufen – es blockiert jeden Merge, der gegen die Traceability-Invarianten verstößt.
