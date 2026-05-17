---
id: TST-0080
project: PRJ-0001
title: "Tests: LogStreamer + LogEventBus (CON-0070)"
contract: CON-0070
contracts: ["CON-0070"]
spec: SPEC-0022
level: contract
status: draft
artifact: "tests/unit/test_tst_0080.py"
---

# Test: LogStreamer und LogEventBus

> **Contract:** CON-0070 · **Typ:** Contract-Test · **Status:** draft

## Abgedeckte Garantien

- CON-0070 G-03: Buffer-History bei Verbindungsaufbau
- CON-0070 G-04: Sauberes Detach (kein Zombie-Thread)
- CON-0070 G-05: Multicast an N Clients
- CON-0070 INV-01: Buffer-Limit FIFO
- CON-0070 INV-03: Client-Disconnect stoppt nicht den Stream

## Test-Datei

`tests/unit/test_tst_0080.py`
