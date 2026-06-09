---
id: TST-0182
title: Pre-Commit-Hook gibt Exit 1 bei rotem Spec-Test
spec: SPEC-0041
contract: CON-0155
level: contract
status: draft
---
## Was wird geprüft?

Der installierte `pre-commit`-Hook blockiert Commits die `main.py`,
`routes/` oder `App.tsx` betreffen wenn die zugehörigen Spec-Tests rot sind.

## Test-Cases

1. **Blocking bei rotem Test:** Staged-Diff enthält `routes/dag_monitor.py`,
   zugehöriger pytest-Lauf schlägt fehl → Hook Exit-Code 1, Commit
   wird abgebrochen, Fehlermeldung nennt den fehlschlagenden Test

2. **Kein Blocking bei grünen Tests:** Staged-Diff enthält `main.py`,
   alle zugehörigen Tests grün → Hook Exit-Code 0, Commit läuft durch

3. **Keine betroffenen Dateien:** Staged-Diff enthält nur `README.md` →
   Hook führt keine Tests aus, Exit-Code 0

4. **Keine Spec-ID ermittelbar:** Datei in `routes/` ist keiner Spec
   zugeordnet → Hook überspringt Test-Ausführung, Exit-Code 0

5. **compliance.post_commit_hook: false:** Auch bei rotem Test →
   Hook gibt Exit-Code 0 (deaktiviert)
