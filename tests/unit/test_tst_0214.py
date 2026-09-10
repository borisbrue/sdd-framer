# TST-0214 – sdd init Autonomie-Provisioning
# Spec: SPEC-0051 · Contract: CON-0188
import json
import stat
from pathlib import Path

from sdd_cli.init import copy_guardrail_hook, merge_claude_settings, write_autonomous_local


def _make_blueprint(tmp: Path) -> Path:
    bp = tmp / "blueprint"
    claude = bp / "templates" / "agents-md" / "providers" / "claude"
    claude.mkdir(parents=True)
    (claude / "settings.json").write_text(json.dumps({
        "permissions": {"allow": ["Bash(sdd *)"]},
        "hooks": {"PreToolUse": [{
            "matcher": "Bash",
            "hooks": [{"type": "command",
                       "command": 'bash "$CLAUDE_PROJECT_DIR/.claude/hooks/autonomous-guardrail.sh"'}],
        }]},
    }), encoding="utf-8")
    hooks = bp / ".claude" / "hooks"
    hooks.mkdir(parents=True)
    (hooks / "autonomous-guardrail.sh").write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    return bp


def _guardrail_blocks(settings: dict) -> list:
    return [
        b for b in settings.get("hooks", {}).get("PreToolUse", [])
        if any("autonomous-guardrail.sh" in h.get("command", "") for h in b.get("hooks", []))
    ]


class TestTST0214:
    def test_copy_guardrail_hook_executable(self, tmp_path) -> None:
        bp = _make_blueprint(tmp_path)
        target = tmp_path / "proj"
        target.mkdir()
        copy_guardrail_hook(target, bp)
        hook = target / ".claude" / "hooks" / "autonomous-guardrail.sh"
        assert hook.exists()
        assert hook.stat().st_mode & stat.S_IXUSR  # ausführbar (INV-01)

    def test_merge_adds_hook_and_preserves_allow(self, tmp_path) -> None:
        bp = _make_blueprint(tmp_path)
        target = tmp_path / "proj"
        (target / ".claude").mkdir(parents=True)
        (target / ".claude" / "settings.json").write_text(
            json.dumps({"permissions": {"allow": ["Bash(ls)"]}}), encoding="utf-8")
        merge_claude_settings(target, bp)
        s = json.loads((target / ".claude" / "settings.json").read_text())
        assert "Bash(ls)" in s["permissions"]["allow"]   # bestehende allow erhalten (INV-02)
        assert len(_guardrail_blocks(s)) == 1            # Hook gemerged (INV-01)

    def test_merge_hook_idempotent(self, tmp_path) -> None:
        bp = _make_blueprint(tmp_path)
        target = tmp_path / "proj"
        (target / ".claude").mkdir(parents=True)
        merge_claude_settings(target, bp)
        merge_claude_settings(target, bp)
        s = json.loads((target / ".claude" / "settings.json").read_text())
        assert len(_guardrail_blocks(s)) == 1            # kein Duplikat (INV-02)

    def test_autonomous_writes_local_only(self, tmp_path) -> None:
        target = tmp_path / "proj"
        target.mkdir()
        write_autonomous_local(target)
        local = json.loads((target / ".claude" / "settings.local.json").read_text())
        assert local["permissions"]["defaultMode"] == "bypassPermissions"   # INV-04
        assert "settings.local.json" in (target / ".gitignore").read_text()  # INV-04
        committed = target / ".claude" / "settings.json"
        assert not committed.exists() or "defaultMode" not in committed.read_text()  # INV-03/04
