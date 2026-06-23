"""Autonomer Bypass-Guardrail – Kommando-Block-Policy (SPEC-0051).

Strategy: jede Block-Regel ist eine unabhängige Funktion (segment, tokens) -> reason|None.
Chain of Responsibility: evaluate_command wertet die Regeln je Kommando-Segment der Reihe
nach aus und blockt beim ersten Treffer.

Schlüssel zur Vermeidung von False Positives (ggü. dem alten Bash-Regex-Guardrail):
- Segment-Split nur an Statement-Trennern (`;`, `&&`, `||`), NICHT an Pipes `|`.
- Tokenisierung via shlex → ein Gefahrenmuster in einem gequoteten Argument
  (Commit-Message, echo) ist ein Token, kein Kommando → löst nicht aus.
- Force-Flags werden exakt erkannt (`--force`, `--force-with-lease`, isoliertes `-f`),
  nicht über ein breites `-*f*`-Teilmuster (das `--body-file` traf).
"""
from __future__ import annotations

import re
import shlex
from collections.abc import Callable

_SEGMENT_SEP = re.compile(r"&&|\|\||;")
_ENV_ASSIGN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
_PROTECTED = {"main", "master"}
_FORCE_FLAGS = {"-f", "--force", "--force-with-lease"}
_CATASTROPHIC_RM = {"/", "/*", "~", "~/", "$HOME"}


def _split_segments(command: str) -> list[str]:
    return [s.strip() for s in _SEGMENT_SEP.split(command) if s.strip()]


def _tokenize(segment: str) -> list[str]:
    try:
        return shlex.split(segment)
    except ValueError:
        return segment.split()


def _effective(tokens: list[str]) -> tuple[str, list[str]]:
    """Überspringt Env-Zuweisungen und sudo/doas/env-Präfixe → (cmd, rest)."""
    i = 0
    while i < len(tokens) and _ENV_ASSIGN.match(tokens[i]):
        i += 1
    if i < len(tokens) and tokens[i] in ("sudo", "doas", "env"):
        i += 1
        while i < len(tokens) and _ENV_ASSIGN.match(tokens[i]):
            i += 1
    if i >= len(tokens):
        return "", []
    return tokens[i], tokens[i:]


def _has_protected_ref(tokens: list[str]) -> bool:
    for t in tokens:
        if t in _PROTECTED:
            return True
        if ":" in t and t.split(":")[-1] in _PROTECTED:  # refspec local:remote
            return True
        if t.split("/")[-1] in _PROTECTED and "/" in t:   # origin/main
            return True
    return False


def _is_recursive_force_rm(rest: list[str]) -> bool:
    has_r = has_f = False
    for t in rest[1:]:
        if not t.startswith("-") or t.startswith("--"):
            continue
        body = t[1:]
        if "r" in body.lower():
            has_r = True
        if "f" in body:
            has_f = True
    return has_r and has_f


# ── Regeln (Strategy) ─────────────────────────────────────────────────────────

def _rule_force_push(cmd: str, rest: list[str], seg: str) -> str | None:
    if cmd != "git" or "push" not in rest:
        return None
    if not any(t in _FORCE_FLAGS for t in rest):
        return None
    if _has_protected_ref(rest):
        return ("Guardrail: Force-Push auf main/master ist blockiert. "
                "Force-Push nur auf Feature-Branches.")
    return None


def _rule_remote_delete(cmd: str, rest: list[str], seg: str) -> str | None:
    if cmd != "git" or "push" not in rest:
        return None
    deleting = "--delete" in rest or "-d" in rest or any(t.startswith(":") for t in rest)
    if deleting and _has_protected_ref(rest):
        return "Guardrail: Löschen des Remote-Branches main/master ist blockiert."
    return None


def _rule_rm_rf(cmd: str, rest: list[str], seg: str) -> str | None:
    if cmd != "rm" or not _is_recursive_force_rm(rest):
        return None
    for t in rest[1:]:
        if t.startswith("-"):
            continue
        if t in _CATASTROPHIC_RM or t.startswith("~/") or t.startswith("$HOME") \
           or t == ".." or t.startswith("../"):
            return ("Guardrail: 'rm -rf' auf / ~ $HOME oder Parent-Pfade ist blockiert. "
                    "Lösche nur gezielte Pfade im Repo.")
    return None


def _rule_disk_wipe(cmd: str, rest: list[str], seg: str) -> str | None:
    if cmd == "dd" and any(t.startswith("of=/dev/") for t in rest):
        return "Guardrail: Direktes Beschreiben eines Datenträgers (dd) ist blockiert."
    if cmd == "wipefs" or cmd == "mkfs" or cmd.startswith("mkfs."):
        return "Guardrail: Formatieren eines Datenträgers (mkfs/wipefs) ist blockiert."
    return None


def _rule_net_pipe_shell(cmd: str, rest: list[str], seg: str) -> str | None:
    if cmd not in ("curl", "wget"):
        return None
    if re.search(r"\|\s*(sudo\s+)?(bash|sh|zsh|fish)(\s|$)", seg):
        return "Guardrail: 'curl|bash'/'wget|sh' (Code aus dem Netz ausführen) ist blockiert."
    return None


def _rule_chmod_chown_root(cmd: str, rest: list[str], seg: str) -> str | None:
    if cmd not in ("chmod", "chown"):
        return None
    recursive = any(t in ("-R", "-r") or (t.startswith("-") and "R" in t[1:]) for t in rest[1:])
    if recursive and "/" in rest[1:]:
        return "Guardrail: rekursives chmod/chown auf / ist blockiert."
    return None


_RULES: tuple[Callable[[str, list[str], str], str | None], ...] = (
    _rule_force_push,
    _rule_remote_delete,
    _rule_rm_rf,
    _rule_disk_wipe,
    _rule_net_pipe_shell,
    _rule_chmod_chown_root,
)


def evaluate_command(command: str) -> str | None:
    """Gibt einen Block-Grund zurück, wenn das Kommando gefährlich ist, sonst None."""
    if not command or not command.strip():
        return None
    for segment in _split_segments(command):
        tokens = _tokenize(segment)
        if not tokens:
            continue
        cmd, rest = _effective(tokens)
        if not cmd:
            continue
        for rule in _RULES:
            reason = rule(cmd, rest, segment)
            if reason:
                return reason
    return None


def decide(hook_input: dict) -> dict | None:
    """PreToolUse-Hook-Input → permissionDecision-Dict (deny) oder None (allow)."""
    command = ((hook_input or {}).get("tool_input") or {}).get("command", "")
    reason = evaluate_command(command)
    if reason is None:
        return None
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }
