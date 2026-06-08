---
id: TST-0177
title: "Hub-Verbindungsmonitor (ConnectionMonitor) und Aktionssperre (canStart/canStop)"
level: unit
spec: SPEC-0040
contract: CON-0150
status: implemented
framework: deno
artifact: "web/pwa/src/__tests__/tst_0177.test.ts"
tags: []
---

Prüft die reine Logik in `hubLogic.ts`:
- `ConnectionMonitor`: Initialzustand, Entprellung (EC-10), Wiederverbindung (FR-08)
- `canStart` / `canStop`: Aktionssperre bei offline/pending/falschem Status (FR-05, EC-04)
- `optimisticStatus`: korrekter Übergangsstatus (FR-07)
- `isTransitionState`: erkennt starting/stopping korrekt (EC-03)
