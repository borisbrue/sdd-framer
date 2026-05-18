# AGENTS.md

> Dieses Dokument gibt Code-generierenden Agenten den nötigen Kontext über dieses Repository.
> Es wird von `sdd validate` auf Vollständigkeit geprüft.
> **Fülle alle Sektionen aus** — unvollständige Sektionen reduzieren die Code-Qualität des Agenten.

## Service-Zweck

<!-- Was tut dieser Service / diese Anwendung? Ein Satz, dann 2-3 Details. -->

Dieser Service ...

## Architektur

<!-- Welche Schichten gibt es? Welches Muster (Hexagonal, MVC, Event-Driven, ...)? -->

- **Typ:** <!-- Monolith | Microservice | Library | CLI | Worker -->
- **Schichten:** <!-- z.B. API → Service → Repository → DB -->
- **Externe Systeme:** <!-- z.B. PostgreSQL, Redis, GitHub API -->

## Verzeichnisstruktur

<!-- Die wichtigsten Verzeichnisse und ihre Aufgabe. -->

```
/
├── src/          # Hauptquellcode
├── tests/        # Automatisierte Tests
├── docs/         # Dokumentation
└── .sdd/         # SDD-Konfiguration (Specs, Contracts, Holdout)
```

## Externe Abhängigkeiten

<!-- Welche externen Services / APIs werden aufgerufen? -->

| Service        | Zweck              | Env-Variable        |
|----------------|--------------------|---------------------|
| <!-- name -->  | <!-- zweck -->     | <!-- VAR_NAME -->   |

## Build- und Start-Befehle

```bash
# Abhängigkeiten installieren
# <install-command>

# Entwicklungsserver starten
# <dev-command>

# Tests ausführen
# <test-command>

# Produktions-Build
# <build-command>
```

## Linting- und Formatierungsregeln

<!-- Welche Linter / Formatter laufen in CI? Welche Regeln sind kritisch? -->

- **Formatter:** <!-- z.B. black, prettier, gofmt -->
- **Linter:** <!-- z.B. ruff, eslint, golangci-lint -->
- **Kritische Regeln:** <!-- Was bricht den Build? -->

## Taste Invariants

<!-- Kleine, versionierte Regelsets die als harte CI-Fehler durchgesetzt werden (nie als Warnings).
     Agenten dürfen diese Regeln NIEMALS mit Inline-Suppress-Kommentaren umgehen. -->

- **Inline-Disable verboten:** Unterdrücke niemals Linter-Fehler durch Inline-Kommentare
  (z.B. `# noqa`, `// eslint-disable-next-line`, `@SuppressWarnings`, `# type: ignore`).
  Beheble die Ursache — unterdrücke nicht den Fehler.
- <!-- Weitere Taste Invariants, z.B.: -->
  <!-- - "Alle REST-Endpunkte brauchen Auth-Annotations" -->
  <!-- - "Services importieren nie aus der Controller-Schicht" -->
  <!-- - "Logging ausschließlich via structlog/logger.info, kein print/console.log" -->

## Konventionen

<!-- Wichtige Konventionen, die der Agent kennen muss. -->

- Namenskonventionen: ...
- Commit-Format: ...
- Fehlerbehandlung: ...

## SDD-Kontext

<!-- Welche Specs, Contracts und Holdout-Szenarien sind relevant für neue Features? -->

- Specs: `specs/` — definieren WAS gebaut werden soll
- Contracts: `contracts/` — definieren WIE die Schnittstellen aussehen
- Holdout: `.sdd/holdout/` — **nicht lesen** (Test-Isolation)
