# SPEC-0102: Dateimengen für Quality-Gates

## 1. Zusammenfassung

Quality-Gates bekommen eine Dateiliste (`{paths}`), die über Glob-Muster in der Konfiguration
bestimmt wird (`include`, `exclude`). Die Muster folgen der gitignore-/ripgrep-Konvention mit `**`.
Pfade sind immer relativ zur Projektwurzel und verwenden `/`.

## 3. Nicht-Ziele

- Keine Zeichenklassen (`[abc]`), keine Negation (`!muster`), keine Klammer-Alternativen (`{a,b}`).
- Keine Symlink-Behandlung.

## 4. Funktionale Anforderungen

- **FR-01:** `glob_match(path, pattern) -> bool` prüft, ob der **ganze** Pfad dem Muster entspricht.
  `*` steht für beliebig viele Zeichen außer `/`, `?` für genau ein Zeichen außer `/`. Alle anderen
  Zeichen (auch `.`, `+`, `(`) sind literal.
- **FR-02:** `**/` steht für null oder mehr vollständige Verzeichnisebenen: `**/test_*.py` trifft
  `test_a.py` ebenso wie `pkg/sub/test_a.py`. Ein `**` ohne folgenden `/` steht für beliebige
  Zeichen einschließlich `/`.
- **FR-03:** Ein Muster, das auf `/**` endet, trifft alles *unterhalb* des Verzeichnisses (mindestens
  ein weiteres Zeichen nach dem `/`), nicht aber das Verzeichnis selbst: `.sdd/**` trifft
  `.sdd/config.yaml`, aber weder `.sdd` noch `.sddrc`.
- **FR-04:** `matches_any(path, patterns) -> bool` ist wahr, wenn mindestens ein Muster trifft; bei
  leerer Musterliste falsch.
- **FR-05:** `collect_files(root: Path, include: list[str], exclude: list[str]) -> list[str]` liefert
  alle Dateien (keine Verzeichnisse) unter `root` als relative Pfade mit `/`, alphabetisch
  sortiert. Leeres `include` bedeutet „alle Dateien“. Dateien, die ein `exclude`-Muster treffen,
  entfallen; `.sdd/**` und `.git/**` sind immer ausgeschlossen.
