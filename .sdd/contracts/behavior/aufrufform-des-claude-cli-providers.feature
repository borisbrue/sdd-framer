# language: de
Funktionalität: Aufrufform des claude-cli-Providers
  Als Pipeline im keyfreien Betrieb
  möchte ich claude als reine Completion-Engine aufrufen
  um keinen Claude-Code-Overhead pro Aufruf zu bezahlen

  Szenario: Agent-Fähigkeiten sind abgeschaltet
    Wenn der Provider complete("Hallo") aufruft
    Dann enthält der claude-Aufruf --tools "", --setting-sources "" und --strict-mcp-config
    Und die Umgebung des Kindprozesses enthält CLAUDE_CODE_DISABLE_AUTO_MEMORY=1
    Und die übrige Umgebung ist unverändert

  Szenario: System-Prompt als echter System-Prompt
    Wenn der Provider complete("Hallo", system_prompt="Sei knapp.") aufruft
    Dann enthält der claude-Aufruf --system-prompt "Sei knapp."
    Und claude liest über stdin genau "Hallo"

  Szenario: Ohne System-Prompt
    Wenn der Provider complete("Hallo") aufruft
    Dann enthält der claude-Aufruf --system-prompt ""
    Und claude liest über stdin genau "Hallo"

  Szenario: Großer Prompt
    Angenommen ein Prompt mit 200.000 Zeichen
    Wenn der Provider ihn aufruft
    Dann liest claude ihn vollständig über stdin
    Und er steht nicht in der Argumentliste

  Szenario: CLI scheitert ohne Envelope
    Angenommen claude endet mit Exit-Code 2, leerem stdout und stderr "error: unknown option '--tools'"
    Wenn der Provider complete("Hallo") aufruft
    Dann wirft er RuntimeError mit "2" und "unknown option"

  Szenario: Umlaute und Sonderzeichen
    Wenn der Provider complete("Grüße – ✓") aufruft
    Dann liest claude über stdin genau "Grüße – ✓"

  Szenario: Lange Fehlermeldung wird gekürzt
    Angenommen claude endet mit Exit-Code 3, leerem stdout und 1.500 Zeichen stderr
    Wenn der Provider complete("Hallo") aufruft
    Dann enthält der RuntimeError nur die letzten 500 Zeichen von stderr

  Szenario: CLI scheitert mit JSON ohne result
    Angenommen claude endet mit Exit-Code 1 und gibt {"type":"result","is_error":true} aus
    Wenn der Provider complete("Hallo") aufruft
    Dann wirft er RuntimeError mit "1"

  Szenario: CLI scheitert mit Envelope
    Angenommen claude endet mit Exit-Code 1 und liefert ein Envelope mit result "Fehlertext"
    Wenn der Provider complete("Hallo") aufruft
    Dann gibt er "Fehlertext" zurück
