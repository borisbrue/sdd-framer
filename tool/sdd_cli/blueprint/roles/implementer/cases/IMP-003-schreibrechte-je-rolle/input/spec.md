# SPEC-0103: Schreibrechte der Pipeline-Rollen (PathPolicy)

## 1. Zusammenfassung

Die Agenten-Pipeline lässt LLM-Rollen Dateien schreiben. Bevor eine Datei geschrieben wird, fragt
der Runner `PathPolicy.check(role, path, task)`. Default ist *deny*. Das Ergebnis hängt nur von
Rolle, Task, Pfad und den konfigurierten `protected_paths` ab.

## 2. Kontext

- Rollen: `decomposer`, `test_author`, `implementer`, `reviewer`, `supervisor`.
- Ein Task ist ein dict mit u. a. `test_file` (str, optional) und `allowed_paths` (Liste von
  Glob-Mustern, optional).
- Glob-Muster folgen SPEC-0102 und sind in `sddlib/globs.py` (`glob_match`, `matches_any`)
  bereits umgesetzt.

## 4. Funktionale Anforderungen

- **FR-01:** `normalize(path: str) -> str | None` wandelt `\` in `/` um und normalisiert den Pfad
  (`./a/../b` → `b`). Absolute Pfade (beginnend mit `/`) und Pfade, die nach der Normalisierung
  aus der Projektwurzel herausführen (`..` oder `../…`), ergeben `None`.
- **FR-02:** `check` liefert ein unveränderliches `PolicyDecision(allowed: bool, reason: str | None)`.
  Die Regeln gelten in dieser Reihenfolge, die erste zutreffende entscheidet:
  1. Pfad nicht normalisierbar (FR-01) → verweigert, Grund `"geschützter Pfad"`.
  2. Rolle ist weder `test_author` noch `implementer` → verweigert, Grund
     `"Rolle <rolle> schreibt nicht"`.
  3. Pfad ist geschützt (FR-03) → verweigert, `"geschützter Pfad"`.
  4. Pfad ist die (normalisierte) `test_file` des Tasks → für `test_author` erlaubt, sonst
     verweigert mit `"Testdatei des Tasks"`.
  5. Rolle `test_author` → verweigert, `"test_author schreibt nur die Testdatei"`.
  6. `allowed_paths` gesetzt und nicht leer und kein Muster trifft → verweigert,
     `"außerhalb allowed_paths"`.
  7. Sonst erlaubt (`reason` ist `None`).
- **FR-03:** Geschützt sind immer `.sdd/**`, `specs/**`, `contracts/**` sowie die Verzeichnisse
  `.sdd`, `specs`, `contracts` selbst, zusätzlich alle Muster aus `protected_paths`.
- **FR-04:** `PathPolicy(root: Path, protected_paths: Iterable[str] = ())` speichert `root`; die
  zusätzlichen Muster ergänzen die Standardmuster, ersetzen sie nicht.
- **FR-05:** `PathPolicy.from_config(root, raw_config)` liest `raw_config["pipeline"]["protected_paths"]`;
  fehlt der Abschnitt oder ist er `None`, gibt es keine zusätzlichen Muster.
- **FR-06:** Die Prüfung verändert das Dateisystem nicht und hängt nicht davon ab, ob der Pfad
  existiert.
