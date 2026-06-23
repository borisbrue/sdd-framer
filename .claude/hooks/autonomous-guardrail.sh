#!/usr/bin/env bash
# Autonomous-Guardrail (PreToolUse, matcher: Bash)
#
# Läuft bei JEDEM Bash-Tool-Call — auch unter permissions.defaultMode=bypassPermissions,
# da PreToolUse-Hooks nur den Permission-PROMPT, nicht die Hook-Ausführung überspringen.
# Blockt eine kleine, scharf umrissene Menge katastrophaler/irreversibler Kommandos.
# Alles andere fällt durch (kein Output, exit 0) → normaler Permission-Fluss / Bypass.
#
# Bewusst NICHT geblockt (gehört zum sdd-framer-Alltag):
#   rm -f <datei>, rm -rf web/ui/dist, git push origin feat/...,
#   uv tool install, rsync/cp in site-packages, pkill/kill <pid>.
set -euo pipefail

input="$(cat)"
cmd="$(printf '%s' "$input" | jq -r '.tool_input.command // empty' 2>/dev/null || true)"

# Leeres Kommando → nichts zu prüfen
[ -z "$cmd" ] && exit 0

deny() {
  # $1 = Begründung
  jq -nc --arg r "$1" '{
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      permissionDecision: "deny",
      permissionDecisionReason: $r
    }
  }'
  exit 0
}

low="$(printf '%s' "$cmd" | tr '[:upper:]' '[:lower:]')"

# 1) Force-Push auf einen geschützten Branch (main/master)
if printf '%s' "$low" | grep -Eq 'git[[:space:]].*push' \
   && printf '%s' "$low" | grep -Eq '(--force-with-lease|--force|[[:space:]]-f([[:space:]]|$)|-[a-z]*f[a-z]*[[:space:]]+)' \
   && printf '%s' "$low" | grep -Eq '(^|[[:space:]/:])(main|master)([[:space:]]|$)'; then
  deny "Guardrail: Force-Push auf main/master ist im autonomen Modus blockiert. Force-Push nur auf Feature-Branches, oder manuell außerhalb des autonomen Laufs."
fi

# 2) Remote-Branch main/master löschen
if printf '%s' "$low" | grep -Eq 'git[[:space:]].*push' \
   && printf '%s' "$low" | grep -Eq '(--delete|[[:space:]]-d[[:space:]]|[[:space:]]:)(.*)(main|master)'; then
  deny "Guardrail: Löschen des Remote-Branches main/master ist blockiert."
fi

# 3) Katastrophales rekursives Löschen (Root / Home / Parent)
if printf '%s' "$low" | grep -Eq 'rm[[:space:]]+(-[a-z]*r[a-z]*f|-[a-z]*f[a-z]*r|-r[[:space:]]+-f|-f[[:space:]]+-r)' \
   && printf '%s' "$cmd" | grep -Eq '([[:space:]]|=)(/|/\*|~|~/|\$HOME|/\*|\.\.)([[:space:]]|/|\*|$)'; then
  deny "Guardrail: 'rm -rf' auf / ~ \$HOME oder Parent-Pfade ist blockiert. Lösche nur gezielte Pfade innerhalb des Repos."
fi

# 4) Datenträger überschreiben
if printf '%s' "$low" | grep -Eq '(^|[[:space:]])dd[[:space:]].*of=/dev/' \
   || printf '%s' "$low" | grep -Eq '(^|[[:space:]])(mkfs(\.[a-z0-9]+)?|wipefs)[[:space:]]' \
   || printf '%s' "$low" | grep -Eq '>[[:space:]]*/dev/(sd|nvme|mmcblk|disk)'; then
  deny "Guardrail: Direktes Beschreiben/Formatieren von Datenträgern ist blockiert."
fi

# 5) Pipe aus dem Netz direkt in eine Shell (Supply-Chain-Risiko)
if printf '%s' "$low" | grep -Eq '(curl|wget)[[:space:]].*\|[[:space:]]*(sudo[[:space:]]+)?(bash|sh|zsh|fish)([[:space:]]|$)'; then
  deny "Guardrail: 'curl|bash'/'wget|sh' (Code aus dem Netz direkt ausführen) ist blockiert."
fi

# 6) chmod/chown -R auf Root
if printf '%s' "$low" | grep -Eq '(chmod|chown)[[:space:]].*-r.*[[:space:]]/([[:space:]]|$)'; then
  deny "Guardrail: rekursives chmod/chown auf / ist blockiert."
fi

# Alles andere: erlauben (kein Output → normaler Permission-/Bypass-Fluss)
exit 0
