---
id: TST-0191
title: "sdd evaluate --smoke Selbsttest (Acceptance)"
spec: SPEC-0042
contract: CON-0163
level: acceptance
artifact: "tests/acceptance/test_tst_0191.py"
status: draft
---

# Test: sdd evaluate --smoke Selbsttest

> **Contract:** CON-0163 · **Spec:** SPEC-0042 · **Level:** acceptance

## Testfälle

| TC | Beschreibung                                              | Erwartet                                     |
|----|-----------------------------------------------------------|----------------------------------------------|
| 01 | `--smoke` läuft durch → Exit 0                            | Exit 0                                       |
| 02 | Ausgabe enthält "✓ Tier-Sortierung korrekt"               | String in stdout                             |
| 03 | Ausgabe enthält "✓ Fail-Fast critical→normal korrekt"     | String in stdout                             |
| 04 | Ausgabe enthält "✓ Fail-Fast normal→edge-case korrekt"    | String in stdout                             |
| 05 | Laufzeit < 2 s                                            | time.time() delta < 2.0                      |
| 06 | Kein HTTP-Aufruf während --smoke                          | requests/httpx nicht aufgerufen (Mock-Check) |
