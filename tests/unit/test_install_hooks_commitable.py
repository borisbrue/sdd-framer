"""Der installierte pre-commit-Hook muss das Repository commit-faehig lassen.

`sdd install-hooks` schrieb `sdd status-check --fix || exit 1` als erste Zeile.
`sdd status-check` ist seit SPEC-0044 kein oeffentlicher Befehl mehr und bricht
jeden Aufruf mit exit 1 ab — danach war in dem Repository kein `git commit` mehr
moeglich. CON-0167 verlangt beides: das Kommando nicht mehr oeffentlich, die
Logik aber weiterhin im Hook lauffaehig.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tool"))


def _hook_script() -> str:
    """Das Skript, das install-hooks schreibt — aus der Quelle gelesen."""
    src = (Path(__file__).resolve().parents[2]
           / "tool" / "sdd_cli" / "main.py").read_text(encoding="utf-8")
    m = re.search(r'hook_script = \(\n(.*?)\n    \)', src, re.DOTALL)
    assert m, "hook_script in main.py nicht gefunden"
    parts = re.findall(r'"((?:[^"\\]|\\.)*)"', m.group(1))
    # Die Literale stammen aus dem Quelltext: \n ist dort zweizeichig.
    return "".join(parts).encode().decode("unicode_escape")


class TestHookScript:
    def test_does_not_call_retired_status_check(self):
        assert "sdd status-check" not in _hook_script()

    def test_calls_the_gate(self):
        assert "sdd pre-commit-gate" in _hook_script()

    def test_every_referenced_sdd_command_exits_zero_on_a_clean_tree(self, tmp_path):
        """Die Absicherung: kein Befehl im Hook darf ohne Anlass abbrechen.

        Genau das war der Defekt — die Zeile stand im Hook und brach immer ab.
        Im leeren Verzeichnis fehlt .sdd/config.yaml, der Gate-Pfad kehrt sofort
        zurueck; die Pruefung kostet damit keine Testlaufzeit.
        """
        commands = [
            line.split()[1]
            for line in _hook_script().splitlines()
            if line.startswith("sdd ")  # Kommentar- und Shebang-Zeilen ausklammern
        ]
        assert commands, "Hook ruft gar kein sdd-Kommando auf"
        for cmd in commands:
            proc = subprocess.run(
                [sys.executable, "-m", "sdd_cli.main", cmd],
                cwd=tmp_path, capture_output=True, text=True,
                env={**__import__("os").environ,
                     "PYTHONPATH": str(Path(__file__).resolve().parents[2] / "tool")},
            )
            assert proc.returncode == 0, (
                f"`sdd {cmd}` bricht mit exit {proc.returncode} ab und macht damit "
                f"jeden Commit unmoeglich:\n{proc.stdout}{proc.stderr}"
            )


class TestStatusCheckRunsInternally:
    """CON-0167: 'pre-commit-Hook-Funktionalitaet bleibt erhalten'."""

    def _project(self, root: Path, status: str = "approved") -> Path:
        (root / ".sdd" / "specs").mkdir(parents=True)
        (root / ".sdd" / "contracts").mkdir(parents=True)
        (root / ".sdd" / "config.yaml").write_text("version: 1\n", encoding="utf-8")
        spec = root / ".sdd" / "specs" / "SPEC-0001-demo.md"
        spec.write_text(
            f"---\nid: SPEC-0001\ntitle: Demo\nstatus: {status}\nowner: B\n"
            f"version: 0.1.0\n---\n\n# Demo\n\nUrsprung.\n", encoding="utf-8")
        return spec

    def test_content_change_resets_status_to_review(self, tmp_path):
        from sdd_cli.config import load_config
        from sdd_cli.lifecycle import rebuild_hashes, save_hashes
        from sdd_cli.pre_commit_hook import apply_status_transitions

        spec = self._project(tmp_path)
        cfg = load_config(tmp_path)
        save_hashes(cfg, rebuild_hashes(cfg))

        spec.write_text(spec.read_text(encoding="utf-8").replace("Ursprung.", "Geaendert."),
                        encoding="utf-8")
        changes = apply_status_transitions(tmp_path)

        assert [c.artifact_id for c in changes] == ["SPEC-0001"]
        assert "status: review" in spec.read_text(encoding="utf-8")

    def test_unchanged_content_is_a_noop(self, tmp_path):
        from sdd_cli.config import load_config
        from sdd_cli.lifecycle import rebuild_hashes, save_hashes
        from sdd_cli.pre_commit_hook import apply_status_transitions

        spec = self._project(tmp_path)
        cfg = load_config(tmp_path)
        save_hashes(cfg, rebuild_hashes(cfg))

        assert apply_status_transitions(tmp_path) == []
        assert "status: approved" in spec.read_text(encoding="utf-8")

    def test_failure_does_not_block_the_commit(self, tmp_path):
        """Weiches Scheitern: ohne Projekt darf nichts fliegen und nichts blocken."""
        from sdd_cli.pre_commit_hook import apply_status_transitions

        assert apply_status_transitions(tmp_path) == []
