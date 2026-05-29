<!-- skill: maintenance:release | version: 0.1.0 | sdd-blueprint: false | updated: 2026-05-30 -->

# /maintenance:release – Version bumpen, Wheel bauen und einspielen

## Aufgabe
Erhöht die Versionsnummer, committet, baut ein neues Wheel und installiert es
in alle aktiven sdd-Installationen dieses Projekts.

`$ARGUMENTS` enthält optional die neue Versionsnummer (z.B. `0.1.16`).
Wird keine angegeben, wird die Patch-Nummer automatisch um 1 erhöht.

## Besonderheiten dieses Projekts

Drei Versionsdateien müssen synchron gehalten werden:

| Datei | Warum |
|---|---|
| `pyproject.toml` | Root-Paket `sdd-framer` (Wheel-Metadaten) |
| `tool/pyproject.toml` | CLI-Paket `sdd-cli` (separates Tool-Paket) |
| `tool/sdd_cli/__init__.py` | `__version__` — wird von `sdd --version` gelesen |

Zwei aktive uv-Tool-Installationen müssen aktualisiert werden:

| Installation | Genutzt von |
|---|---|
| `/home/deck/.local/share/uv/tools` | Terminal (System-Shell) |
| `/home/deck/.var/app/com.visualstudio.code/data/uv/tools` | Flatpak VS Code Terminal |

Die `.venv` im Projektverzeichnis ist ein Editable-Install — sie liest direkt aus
`tool/sdd_cli/` und benötigt kein separates Update.

## Schritt 1: Aktuelle Version ermitteln

```bash
grep "^__version__" tool/sdd_cli/__init__.py
```

Falls `$ARGUMENTS` leer: Patch-Version automatisch um 1 erhöhen.
Falls `$ARGUMENTS` gesetzt: diese Version direkt verwenden.

## Schritt 2: Drei Versionsdateien aktualisieren

`pyproject.toml`, `tool/pyproject.toml`, `tool/sdd_cli/__init__.py` — alle auf die neue Version setzen.

## Schritt 3: Committen

```bash
git add pyproject.toml tool/pyproject.toml tool/sdd_cli/__init__.py
git commit -m "version bump <NEUE_VERSION>"
```

## Schritt 4: Wheel bauen

```bash
uv build
```

Erzeugt `dist/sdd_framer-<NEUE_VERSION>-py3-none-any.whl`.

## Schritt 5: In beide Installationen einspielen

```bash
UV_TOOL_DIR=/home/deck/.local/share/uv/tools uv tool install --force dist/sdd_framer-<NEUE_VERSION>-py3-none-any.whl
UV_TOOL_DIR=/home/deck/.var/app/com.visualstudio.code/data/uv/tools uv tool install --force dist/sdd_framer-<NEUE_VERSION>-py3-none-any.whl
```

## Schritt 6: Verifizieren

```bash
sdd --version
```

Erwartete Ausgabe: `sdd, version <NEUE_VERSION>`

Zeige Zusammenfassung: neue Version, Wheel-Pfad, beide Installationen ✓
