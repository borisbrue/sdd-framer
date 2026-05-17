# Specifications

Dieses Verzeichnis enthält die ausführbare Spezifikation des Projekts.

## Struktur

```
specs/
├── vision.md          ← Übergeordnetes Ziel
├── glossary.md        ← Domänensprache
├── constraints.md     ← Globale Rahmenbedingungen
├── SPEC-0001-*.md     ← Feature-Specs
├── SPEC-0002-*.md
└── _archive/          ← Deprecated Specs (nicht löschen, nur verschieben)
```

## Lifecycle

`draft` → `review` → `approved` → `implemented` → ggf. `deprecated`

Nur Specs im Status **approved** oder **implemented** dürfen Code im Hauptzweig erzeugen.

## Workflow

1. **Neue Spec:** `sdd new spec "<Titel>"` legt aus dem Template eine neue Datei mit nächster freier ID an.
2. **Contracts ergänzen:** Jede Spec benötigt mindestens einen Contract. `sdd new contract --spec SPEC-XXXX --type api`.
3. **Tests ergänzen:** Pro Contract mindestens ein Test. `sdd new test --contract CON-XXXX --level contract`.
4. **Validieren:** `sdd validate` prüft Konsistenz, Frontmatter und Verknüpfungen.
5. **Traceability:** `sdd trace` erzeugt die Matrix unter `docs/traceability.md`.

## Konventionen

- Dateinamen: `SPEC-XXXX-kurz-slug.md`
- Eine Spec = ein Feature, nicht eine Komponente.
- Keine Implementierungsdetails in der Spec – das gehört in Contracts und Architektur.
