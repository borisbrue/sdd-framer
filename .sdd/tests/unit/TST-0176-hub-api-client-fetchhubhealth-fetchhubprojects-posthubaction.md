---
id: TST-0176
title: "Hub API Client – fetchHubHealth, fetchHubProjects, postHubAction"
level: unit
spec: SPEC-0040
contract: CON-0147
status: implemented
framework: deno
artifact: "web/pwa/src/__tests__/tst_0176.test.ts"
tags: []
---

Prüft das HTTP-Verhalten der drei Hub-API-Funktionen in `api.ts`:
- `fetchHubHealth`: gibt true/false zurück, wirft nie (CON-0149)
- `fetchHubProjects`: liefert HubProjectList, wirft bei non-200 (CON-0147, CON-0148)
- `postHubAction`: sendet POST an korrekten Endpunkt, wirft bei 4xx/Netzwerkfehler (CON-0147)
