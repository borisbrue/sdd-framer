---
id: TST-0262
title: "Aufrufform des claude-cli-Providers"
level: acceptance            # unit | integration | contract | acceptance | performance | property
spec: SPEC-0067
contract: CON-0233
status: implemented        # planned | implemented | passing | failing | skipped
framework: pytest
artifact: "tests/acceptance/test_con_0233.py"
tags: [llm, claude-cli]
---

# Test: Aufrufform des claude-cli-Providers

> **Level:** acceptance · **Spec:** SPEC-0067 · **Contract:** CON-0233 · **Status:** implemented

## Was wird geprüft?

Der echte `ClaudeCliCompletionProvider` startet einen echten Prozess (SPEC-0067; Datei-Übergabe
des System-Prompts, Timeout und C-Locale seit SPEC-0068 FR-05). An Stelle von `claude`
liegt ein Skript im `PATH`, das Argumente, Umgebung und stdin protokolliert und ein Envelope
ausgibt. Kein Patch von `subprocess.run`: Nur so fällt eine Übergabe über argv bei großen
Prompts wirklich mit `E2BIG` auf.

## Vorbedingungen

- POSIX-Shell und Python im `PATH` (Linux, Dev-Container).

## Ablauf

1. Fake-`claude` in `tmp_path` anlegen, `PATH` darauf zeigen lassen.
2. `complete()` je Szenario aus dem Feature aufrufen.
3. Protokoll des Skripts auswerten.

## Erwartetes Ergebnis

- Argumentliste exakt nach INV-01; System-Prompt aus `--system-prompt-file` (Modus 0600, danach
  gelöscht, auch nach Exit ≠ 0 und Timeout; Kindprozess beendet).
- stdin enthält genau den Prompt, auch bei 200.000 Zeichen.
- Umgebung: `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`, eine vorher gesetzte Testvariable bleibt erhalten.
- Exit 2 ohne Envelope: `RuntimeError` mit Exit-Code und stderr.
- Exit 1 mit Envelope: Text des Envelopes.

Mutationsnachweis (2026-10-06): Exit-Code vor dem Envelope prüfen, `latin-1`, ohne `env`,
stderr ungekürzt und ohne `--strict-mcp-config` lassen jeweils mindestens einen Test rot werden.

## Negativfälle / Edge Cases

- Großer Prompt (200.000 Zeichen) über der argv-Grenze von 128 KiB.
- Fehlschlag mit und ohne Envelope.

## Verknüpfung mit Contract

Dieser Test prüft konkret folgende Punkte aus CON-0233:

- [x] INV-01 Argumentliste
- [x] INV-02 Prompt über stdin
- [x] INV-03 Umgebung
- [x] INV-04 Fehler ohne Envelope

## Hinweise zur Implementierung

Das Fake-Skript ist Python mit Shebang auf `sys.executable`, damit es ohne weitere Abhängigkeit
läuft.
