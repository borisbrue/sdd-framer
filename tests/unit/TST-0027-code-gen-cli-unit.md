---
id: TST-0027
project: PRJ-0001
title: "Orchestrator _call_code_gen via Claude CLI – Unit Test"
level: unit
spec: SPEC-0007
contract: CON-0021
status: implemented
framework: pytest
artifact: "tests/unit/test_execute_flow.py"
tags: ["orchestrator", "claude-cli", "code-gen", "execute-flow"]
---

# Test: Orchestrator _call_code_gen via Claude CLI – Unit Test

Unit-Tests für `orchestrator._call_code_gen()` nach dem Refactor auf Claude Code CLI.

## Test Cases

| TC    | Beschreibung                                           | Erwartet                        |
|-------|--------------------------------------------------------|---------------------------------|
| TC-01 | Erfolgreicher CLI-Aufruf → parst files + explanation   | dict mit files-Liste            |
| TC-02 | claude nicht im PATH → RuntimeError                    | RuntimeError mit "nicht gefunden"|
| TC-03 | CLI gibt non-zero exit → RuntimeError                  | RuntimeError mit exit-Code      |
| TC-04 | CLI-Output enthält Outer-Wrapper → korrekt geparst     | result aus wrapper.result       |
