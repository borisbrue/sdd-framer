---
id: TST-0119
title: "ReviewPipeline + Retry-Logik (Unit)"
level: unit
spec: SPEC-0026
contract: CON-0100
status: draft
---

# TST-0119: ReviewPipeline + Retry-Logik

## Zu prüfendes Verhalten

`task_runner.py` führt die ReviewPipeline korrekt aus und behandelt Retries
und Blockierungen gemäß CON-0100.

## Testfälle

- T01: Alle 3 Stufen bestehen → Task.status == "committed", commit_hash gesetzt (INV-03)
- T02: Syntax-Check schlägt fehl → Unit-Tests + Review werden nicht ausgeführt (INV-01)
- T03: Syntax-Check schlägt fehl → retry_count +1, error_context ergänzt
- T04: 3. Fehlversuch → status == "blocked"
- T05: Retry erhält vollen error_context aller Vorversuche im LLM-Prompt (INV-04)
- T06: error_context wächst monoton, Einträge werden nie gelöscht (INV-02)
- T07: Claude-Review schlägt fehl (Syntax + Tests OK) → retry, error_context enthält Review-Grund
- T08: commit_hash ist None für nicht-committed Tasks (INV-03 Negativ)
