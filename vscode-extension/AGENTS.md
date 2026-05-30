# AGENTS.md – VS Code Extension

> Kontext-Datei für Code-generierende Agenten. Wird von `sdd validate` geprüft.

## Service-Zweck

VS Code Extension für SDD Blueprint: TreeView für Specs/Contracts/Tests,
Diagnostics (Frontmatter-Linting), Go-to-Definition, CodeLens-Annotationen
und Pipeline-Steuerung direkt aus dem Editor.

## Architektur

- **Typ:** VS Code Extension (TypeScript, Extension Host)
- **Schichten:** Extension Entry → Commands/Views → CLI-Bridge (`cli.ts`) → `sdd` CLI
- **Externe Systeme:** SDD Web API (`server.ts`), lokale `sdd`-CLI

```
src/
  extension.ts      # Aktivierung, Command-Registrierung
  cli.ts            # Wrapper für sdd CLI-Aufrufe (child_process)
  server.ts         # HTTP-Client für SDD Web API
  tree.ts           # TreeDataProvider (Specs/Contracts/Tests)
  diagnostics.ts    # Frontmatter-Validierung → VS Code Diagnostics
  codelens.ts       # CodeLens über SPEC/CON/TST-Referenzen
  definition.ts     # Go-to-Definition für IDs
  frontmatter.ts    # YAML-Frontmatter-Parser
  analyzeView.ts    # Webview für Analyse-Ergebnisse
  pipeline.ts       # Pipeline-Status-Polling
```

## Build- und Start-Befehle

```bash
# Abhängigkeiten installieren
npm install

# Extension kompilieren (watch)
npm run watch

# Produktions-Build (.vsix)
npm run package

# Extension in VS Code laden
# F5 in VS Code → Extension Development Host
```

## Linting- und Formatierungsregeln

- **Compiler:** TypeScript strict mode (`tsconfig.json`)
- **Linter:** ESLint mit Standard-VS-Code-Extension-Regeln
- **Kritisch:** Keine `any`-Typen ohne expliziten Kommentar; keine unbenutzten Imports

## Taste Invariants

- **Inline-Disable verboten:** Unterdrücke niemals TypeScript- oder ESLint-Fehler durch
  Inline-Kommentare (`// eslint-disable-next-line`, `// @ts-ignore`, `// @ts-expect-error`).
  Behebbe die Ursache.
- **Kein direktes Filesystem-Schreiben:** Die Extension liest `.sdd/`-Dateien (für
  TreeView/Diagnostics), schreibt aber niemals direkt. Alle Schreiboperationen gehen
  über `cli.ts` → `sdd`-CLI.
- **Kein UI-State in globalen Variablen:** Extension-State ausschließlich über
  `vscode.ExtensionContext` oder dedizierte State-Klassen verwalten.

## Konventionen

- Alle CLI-Aufrufe über `cli.ts` kapseln — nie direkt `child_process.exec` im Feature-Code
- Fehler aus CLI-Calls immer als VS Code `window.showErrorMessage` anzeigen
- Neue Commands in `package.json` `contributes.commands` registrieren und in `extension.ts` binden
- Commit-Format: Konventionelle Commits (`feat:`, `fix:`, `chore:`)

## SDD-Kontext

Relevante Specs für Extension-Features:
- SPEC-0003 / SPEC-0005 / SPEC-0007 — Web API-Endpunkte die die Extension nutzt
- SPEC-0015 — SOLID/Pattern-Check (Extension löst diesen via CLI aus)
- SPEC-0016 — Async-Analyse-Jobs (Extension pollt Status via `pipeline.ts`)
- Holdout: `.sdd/holdout/` — **nicht lesen** (Test-Isolation)
