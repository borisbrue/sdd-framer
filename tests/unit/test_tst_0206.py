"""TST-0206 – sdd vision stats Ausgabe und Fehlerverhalten (Unit)
Spec: SPEC-0047 · Contract: CON-0180
"""
from click.testing import CliRunner

FULL_VISION = """\
# Projekt – Produktvision

## Vision

Ein tolles Produkt.

## Zielgruppe

Entwickler

## Tech Stack

Python

## Competitive Landscape

Niemand

## Kernprobleme

Chaos

## Features

1. **Offline-Modus** – App ohne Internet nutzbar
   > LLM Challenge: Aufwand: high
   > Code Challenge: src/sync.py

2. **Dark Mode** – Dunkles Theme
   > LLM Challenge: Aufwand: low

3. **Export**

## Tasks

- [ ] README aktualisieren
- [x] CI einrichten
- [ ] Docs schreiben
"""

SKELETON = """\
# Projekt – Produktvision

## Vision

## Zielgruppe

## Tech Stack

## Competitive Landscape

## Kernprobleme

## Features

## Tasks
"""


class TestVisionStatsCommand:
    def test_stats_full_vision(self, tmp_path, monkeypatch):
        """INV-02 + Szenario: vollständige Vision → korrekte Zahlen."""
        from tool.sdd_cli.main import cli

        vision_file = tmp_path / "vision.md"
        vision_file.write_text(FULL_VISION)
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".sdd").mkdir()
        (tmp_path / ".sdd" / "vision.md").write_text(FULL_VISION)

        runner = CliRunner()
        result = runner.invoke(cli, ["vision", "stats"])

        assert result.exit_code == 0
        assert "Features:" in result.output
        assert "3" in result.output
        assert "Tasks:" in result.output
        assert "done: 1" in result.output
        assert "offen: 2" in result.output
        assert "LLM Challenges:" in result.output
        assert "Code Challenges:" in result.output

    def test_stats_skeleton_vision(self, tmp_path, monkeypatch):
        """Szenario: leeres Skelett → alle Zahlen 0."""
        from tool.sdd_cli.main import cli

        monkeypatch.chdir(tmp_path)
        (tmp_path / ".sdd").mkdir()
        (tmp_path / ".sdd" / "vision.md").write_text(SKELETON)

        runner = CliRunner()
        result = runner.invoke(cli, ["vision", "stats"])

        assert result.exit_code == 0
        assert "0" in result.output

    def test_stats_missing_vision_exits_nonzero(self, tmp_path, monkeypatch):
        """INV-03 + Szenario: fehlende vision.md → Exit-Code ≠ 0 + sdd vision init Hinweis."""
        from tool.sdd_cli.main import cli

        monkeypatch.chdir(tmp_path)
        (tmp_path / ".sdd").mkdir()

        runner = CliRunner()
        result = runner.invoke(cli, ["vision", "stats"])

        assert result.exit_code != 0
        assert "sdd vision init" in result.output

    def test_stats_output_contains_all_four_categories(self, tmp_path, monkeypatch):
        """INV-02: Ausgabe enthält immer alle vier Kategorien."""
        from tool.sdd_cli.main import cli

        monkeypatch.chdir(tmp_path)
        (tmp_path / ".sdd").mkdir()
        (tmp_path / ".sdd" / "vision.md").write_text(SKELETON)

        runner = CliRunner()
        result = runner.invoke(cli, ["vision", "stats"])

        assert result.exit_code == 0
        output = result.output
        assert "Features:" in output
        assert "Tasks:" in output
        assert "LLM Challenges:" in output
        assert "Code Challenges:" in output

    def test_stats_llm_challenge_count(self, tmp_path, monkeypatch):
        """Szenario: 2 LLM-Challenges, 1 Code-Challenge aus FULL_VISION."""
        from tool.sdd_cli.main import cli

        monkeypatch.chdir(tmp_path)
        (tmp_path / ".sdd").mkdir()
        (tmp_path / ".sdd" / "vision.md").write_text(FULL_VISION)

        runner = CliRunner()
        result = runner.invoke(cli, ["vision", "stats"])

        assert result.exit_code == 0
        lines = result.output.splitlines()
        llm_line = next((zeile for zeile in lines if "LLM Challenges" in zeile), "")
        code_line = next((zeile for zeile in lines if "Code Challenges" in zeile), "")
        assert "2" in llm_line
        assert "1" in code_line
