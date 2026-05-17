---
id: TST-0052
project: PRJ-0001
title: "lifecycle – Audit-Log-Schreibung bei Statusübergang"
level: unit
spec: SPEC-0010
contract: CON-0037
status: draft
framework: pytest
artifact: "tests/unit/test_lifecycle.py"
tags: ["lifecycle", "audit-log", "traceability"]
---

# Test: Audit-Log

Unit-Tests für `lifecycle.write_audit_log()` und Integration in `apply_transitions()`.

## Test Cases

| TC    | Beschreibung                                                                          | Erwartet                                              |
|-------|---------------------------------------------------------------------------------------|-------------------------------------------------------|
| TC-01 | write_audit_log schreibt Zeile im korrekten Format                                   | Zeile enthält Timestamp, ID, alte→neue Status, Grund  |
| TC-02 | apply_transitions ruft write_audit_log für jeden Übergang auf                        | Audit-Log enthält Eintrag pro Übergang                |
| TC-03 | Mehrere Aufrufe appenden (keine Überschreibung)                                      | Log wächst, ältere Einträge bleiben erhalten          |
| TC-04 | Format-Check: `{ISO8601} {ID} {old} → {new} [{reason}]`                              | Regex-Match auf Pflichtformat                          |
