---
id: TST-0083
project: PRJ-0001
title: "Acceptance + Performance: Vollständiger Stack-Flow inkl. Live-Logs"
contract: CON-0069
contracts: ["CON-0069", "CON-0070", "CON-0071", "CON-0073"]
spec: SPEC-0022
level: acceptance
status: draft
artifact: "tests/unit/test_tst_0083.py"
---

# Acceptance Test: Vollständiger Dev-Container-Stack

> **Contracts:** CON-0069, CON-0070, CON-0071, CON-0073 · **Status:** draft

## Testablauf

```
1. sdd dev build  → Image gebaut (gemockt)
2. sdd dev up SPEC-0022 → Stack gestartet, LogStreamer aktiv
3. LogEventBus.publish → Zeile in < 1 s bei WebSocket-Client
4. sdd dev down SPEC-0022 → Stack gestoppt, LogStreamer detached
```

## Test-Datei

`tests/unit/test_tst_0083.py`
