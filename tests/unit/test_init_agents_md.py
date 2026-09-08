"""`sdd init` legte keine AGENTS.md an — die Korrekturanweisung fuehrte im Kreis.

1. `sdd init` legte keine AGENTS.md an.
2. `sdd validate` warnte, dass sie fehlt.
3. Die Anweisung lautete "Run `sdd new agents-md`".
4. Der Befehl antwortete "wurde entfernt -> in sdd init integriert" und endete
   mit exit 1.

Die Vorlage lag im Blueprint und wurde nur nach .sdd/templates/ kopiert, nie in
den Projekt-Root.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tool"))

from sdd_cli.init import init_project

_ROOT = Path(__file__).resolve().parents[2]


class TestInitCreatesAgentsMd:
    def test_agents_md_is_created(self, tmp_path):
        init_project(tmp_path, title="Probe")
        assert (tmp_path / "AGENTS.md").exists()

    def test_content_comes_from_the_blueprint_template(self, tmp_path):
        init_project(tmp_path, title="Probe")
        vorlage = (_ROOT / "tool" / "sdd_cli" / "blueprint" / "templates"
                   / "agents-md" / "default.md").read_text(encoding="utf-8")
        assert (tmp_path / "AGENTS.md").read_text(encoding="utf-8") == vorlage

    def test_it_is_reported_as_created(self, tmp_path):
        result = init_project(tmp_path, title="Probe")
        assert tmp_path.resolve() / "AGENTS.md" in result["created"]

    def test_existing_file_survives_a_second_init(self, tmp_path):
        """Idempotent wie die Skill-Dateien."""
        (tmp_path / "AGENTS.md").write_text("MEIN INHALT\n", encoding="utf-8")
        init_project(tmp_path, title="Probe")
        assert (tmp_path / "AGENTS.md").read_text(encoding="utf-8") == "MEIN INHALT\n"

    def test_force_overwrites(self, tmp_path):
        (tmp_path / "AGENTS.md").write_text("ALT\n", encoding="utf-8")
        init_project(tmp_path, title="Probe", force=True)
        assert (tmp_path / "AGENTS.md").read_text(encoding="utf-8") != "ALT\n"


class TestNoDeadEndAnymore:
    def test_validate_no_longer_points_at_the_removed_command(self):
        """Kommentarzeilen ausklammern: der Erklaertext zur Historie darf den
        Befehl nennen, der ausgegebene Hinweis nicht."""
        src = (_ROOT / "tool" / "sdd_cli" / "validate.py").read_text(encoding="utf-8")
        code = "\n".join(
            zeile for zeile in src.splitlines() if not zeile.lstrip().startswith("#")
        )
        assert "sdd new agents-md" not in code, (
            "validate verweist weiter auf einen Befehl, der mit exit 1 endet"
        )

    def test_readme_no_longer_advertises_the_removed_command(self):
        readme = (_ROOT / "README.md").read_text(encoding="utf-8")
        assert "sdd new agents-md" not in readme
