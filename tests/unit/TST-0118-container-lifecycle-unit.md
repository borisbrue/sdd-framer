---
id: TST-0118
title: "Ausführungsort von Tasks (Unit)"
level: unit
spec: SPEC-0026
contract: CON-0099
status: draft
artifact: "tests/unit/test_tst_0118.py"
---

# TST-0118: Ausführungsort von Tasks

## Zu prüfendes Verhalten

Wo die Tasks einer Spec laufen, gemäß CON-0099 v0.2.0. Jeder Test übt
Produktionscode aus: `TaskLifecycle`, `Task.to_dict`/`from_dict` und
`DistributionOrchestrator`.

Bis #113 lief diese Datei gegen ein `MockContainerRuntime`, das in ihr selbst
definiert war. Die Testfälle T01–T08 beschrieben eine Task-Container-Runtime
(`container.py`, Namensschema `sdd-SPEC-XXXX-<uuid>`, SIGINT-Cleanup), die es
nie gab. CON-0099 v0.2.0 führt sie als entfallene Zusagen.

## Testfälle

- T01: `start_running("local")` → Status `running`, `container_id == "local"` (G-01)
- T02: `start_running` aus `pending` → `InvalidTransitionError`, kein `container_id` (INV-01)
- T03: `container_id` übersteht `to_dict` → `from_dict` (G-04)
- T04: `DistributionOrchestrator.run` → alle Tasks laufen mit `container_id == "local"` (G-02)

Das Aufräumen des Dev-Containers (G-03) prüft `tests/unit/test_finalize_container.py`
(CON-0065 G-06).
