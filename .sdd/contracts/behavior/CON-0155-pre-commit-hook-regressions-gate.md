---
id: CON-0155
title: Pre-Commit-Hook — Blocking Regressions-Gate
type: behavior
format: markdown
spec: SPEC-0041
version: 0.1.0
status: approved
tests:
- TST-0182
---
Der von `sdd install-hooks` installierte `pre-commit`-Hook gibt Exit-Code 1
zurück (blockiert den Commit) wenn Änderungen an `main.py`, `routes/` oder
`App.tsx` mit fehlschlagenden Spec-Tests einhergehen.

**Garantien**

- Der Hook liest `git diff --cached --name-only` und prüft ob Dateien
  matchen: `**/main.py`, `**/routes/*.py`, `**/App.tsx`.
- Bei Treffer: ermittelt betroffene Spec-IDs aus
  `.sdd/tasks/SPEC-XXXX.json` (Felder `commit_hash` oder `spec_id`)
  und führt `pytest tests/ -k "<filter>" --tb=short` aus.
- Bei pytest Exit-Code ≠ 0: Hook gibt Exit-Code 1 zurück — Commit
  wird abgebrochen. Fehlermeldung nennt konkret welche Tests rot sind.
- Bei pytest Exit-Code 0 oder keinen betroffenen Spec-IDs: Hook gibt
  Exit-Code 0 zurück — Commit läuft durch.
- `git commit --no-verify` umgeht den Hook; der Hook selbst kann diesen
  Bypass nicht abfangen. Ein separater `post-commit`-Hook protokolliert
  den Bypass in `.sdd/audit.log` wenn die Datei schreibbar ist — fehlt
  die Datei oder sind die Rechte unzureichend, wird die Protokollierung
  stillschweigend übersprungen (keine Fehlermeldung).
- Der Hook hat kein Timeout über 60 s — bei längeren Test-Suites muss
  der Filter präzise genug sein.
