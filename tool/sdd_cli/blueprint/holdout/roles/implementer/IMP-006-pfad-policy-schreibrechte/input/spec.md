---
id: SPEC-0112
title: "Schreibrechte der Pipeline-Rollen"
status: approved
---
# SPEC-0112: Schreibrechte der Pipeline-Rollen

## 1. Kontext
Die Pipeline lässt LLM-Rollen Dateien schreiben. Jeder Schreibversuch läuft vorher durch eine
`PathPolicy`, die nur von Rolle, Task, Pfad und der Konfiguration abhängt. Grundsatz: Default deny.

## 2. Ziele
- Rollen können Spezifikationen, Contracts und die SDD-Konfiguration nie verändern.
- Der Test-Autor schreibt ausschließlich die Testdatei seines Tasks, der Implementierer nie.

## 3. Nicht-Ziele
- Keine Prüfung, ob Dateien existieren; keine Dateisystemzugriffe.

## 4. Funktionale Anforderungen

- **FR-01:** `normalize(path)` liefert den Pfad relativ zur Projektwurzel mit `/` als Trenner
  (Backslashes werden zu `/`, `.`- und `..`-Segmente werden aufgelöst, z. B. `pkg/./a/../b.py` →
  `pkg/b.py`). Absolute Pfade und Pfade, die nach dem Auflösen die Projektwurzel verlassen
  (`..` oder Beginn mit `../`), ergeben `None`.
- **FR-02:** `PathPolicy.check(role, path, task)` liefert `PolicyDecision(allowed, reason)`. Die
  Regeln gelten in dieser Reihenfolge, die erste zutreffende entscheidet:
  1. Pfad nicht normalisierbar → verweigert, Grund `"geschützter Pfad"`.
  2. Rolle ist weder `test_author` noch `implementer` → verweigert, Grund
     `"Rolle <rolle> schreibt nicht"`.
  3. Pfad trifft ein geschütztes Muster oder ist genau `.sdd`, `specs` oder `contracts` →
     verweigert, Grund `"geschützter Pfad"`.
  4. Pfad ist (normalisiert) die `test_file` des Tasks: `test_author` darf (Grund `None`),
     jede andere Rolle nicht (Grund `"Testdatei des Tasks"`).
  5. Rolle `test_author` und ein anderer Pfad → verweigert, Grund
     `"test_author schreibt nur die Testdatei"`.
  6. Der Task hat nicht-leere `allowed_paths` (Glob-Muster) und der Pfad trifft keines →
     verweigert, Grund `"außerhalb allowed_paths"`.
  7. Sonst erlaubt (Grund `None`).
- **FR-03:** Geschützt sind immer `.sdd/**`, `specs/**` und `contracts/**`, dazu die Muster aus
  dem Konstruktorargument `protected_paths`. `PathPolicy.from_config(raw)` liest sie aus
  `raw["pipeline"]["protected_paths"]`; fehlt `pipeline` oder der Schlüssel (oder ist er `None`),
  gelten nur die festen Muster.
- **FR-04:** Glob-Muster werden mit `sddlib.globs.matches_any` ausgewertet (`*` ohne `/`, `**`
  über Verzeichnisse).
