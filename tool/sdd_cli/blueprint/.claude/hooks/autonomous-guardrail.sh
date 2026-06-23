#!/usr/bin/env bash
# Autonomous-Guardrail – dünner Wrapper (SPEC-0051, matcher: Bash, PreToolUse).
#
# Delegiert die Block-Entscheidung an `sdd guard check` (Python-Modul sdd_cli/guard.py):
# segment-genau (Split an ; && ||), shlex-tokenisiert, präzise Force-Flag-Erkennung.
# Läuft bei JEDEM Bash-Tool-Call — auch unter permissions.defaultMode=bypassPermissions
# (Hooks laufen unabhängig vom Prompt).
#
# Fail-Safe (FR-08): ist `sdd` nicht erreichbar ODER schlägt `sdd guard check` fehl
# (z. B. alte Version ohne den Befehl), wird das Kommando ERLAUBT (Shell bricht nicht)
# und eine sichtbare [WARN]-Meldung ausgegeben — Bypass ist bewusst gewählt; ein
# Hard-Block aller Kommandos wäre schlimmer als der temporäre Schutzverlust.
set -uo pipefail

# Flatpak-Sandboxes/eingeschränkte Hook-Umgebungen haben ~/.local/bin oft nicht im PATH.
# Angehängt (nicht vorangestellt), damit ein vorhandenes sdd im PATH Vorrang behält.
export PATH="${PATH:-}:$HOME/.local/bin:/usr/local/bin"

warn_allow() {
  printf '%s\n' "{\"systemMessage\":\"[WARN] Guardrail inaktiv: $1 – Kommando ungeprüft erlaubt.\"}"
  exit 0
}

input="$(cat)"
command -v sdd >/dev/null 2>&1 || warn_allow "sdd nicht gefunden"

output="$(printf '%s' "$input" | sdd guard check 2>/dev/null)"
[ $? -ne 0 ] && warn_allow "sdd guard check fehlgeschlagen"

[ -n "$output" ] && printf '%s\n' "$output"
exit 0
