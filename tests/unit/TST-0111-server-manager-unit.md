---
id: TST-0111
project: PRJ-0001
title: "ServerManager – Port-Ermittlung, Lifecycle, Status-Übergänge"
level: unit
spec: SPEC-0017
contract: CON-0054
status: planned
framework: vitest
artifact: "vscode-extension/src/__tests__/server.test.ts"
tags: ["vscode", "server-manager", "lifecycle", "port"]
---

# Test: ServerManager – Port-Ermittlung, Lifecycle, Status-Übergänge

> **Level:** unit · **Spec:** SPEC-0017 · **Contract:** CON-0054 · **Status:** planned

## Was wird geprüft?

- `getStatus()` startet mit `'stopped'`
- `start()` durchläuft `'starting'` → `'running'`
- `stop()` setzt Status auf `'stopped'`
- `getPort()` gibt `null` zurück solange gestoppt
- `getPort()` gibt die ermittelte Portnummer zurück wenn läuft
- `dispose()` ruft intern `stop()` auf (kein Zombie)
- Freier Port wird via Python-Socket korrekt ermittelt (`> 1024`, `< 65535`)
- Bei Python-Fehler: Fallback auf Port 8000

## Ablauf

### TC-01: Initialer Status

1. Instanziiere `ServerManager` mit Mock-OutputChannel
2. Prüfe: `getStatus() === 'stopped'`
3. Prüfe: `getPort() === null`

### TC-02: Status-Sequenz start → running

1. Mock `child_process.spawn` → sendet `"Application startup complete"` auf stdout
2. Rufe `start(root)` auf
3. Prüfe: Status wechselt von `'starting'` → `'running'`
4. Prüfe: `getPort()` ist eine Zahl > 1024

### TC-03: stop() nach start()

1. Starte Server (gemäß TC-02)
2. Rufe `stop()` auf
3. Prüfe: `getStatus() === 'stopped'`
4. Prüfe: `getPort() === null`

### TC-04: dispose() beendet Prozess

1. Starte Server
2. Rufe `dispose()` auf
3. Prüfe: Spawn-Mock hat `kill('SIGTERM')` empfangen

### TC-05: Port-Ermittlung – freier Port

1. Mock `child_process.execSync` für Python-Socket-Befehl → gibt `"54231\n"` zurück
2. Prüfe: `start()` nutzt Port 54231

### TC-06: Port-Ermittlung – Python-Fehler → Fallback 8000

1. Mock `child_process.execSync` → wirft Exception
2. Prüfe: `start()` fällt auf Port 8000 zurück

### TC-07: Server-Crash → Status 'error'

1. Starte Server
2. Mock-Prozess beendet sich mit exit code 1
3. Prüfe: `getStatus() === 'error'`

## Erwartetes Ergebnis

Alle 7 Test-Cases grün. Kein echter Prozess wird gestartet (vollständig gemockt).
