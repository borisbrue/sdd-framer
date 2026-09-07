"""`sdd new adr` existierte nicht, obwohl alles andere dafuer vorhanden war.

Vorlage (blueprint/templates/adr/default.md), ID-Praefix (ids.adr_prefix: ADR),
README-Eintrag und Zielverzeichnis (docs/adr/) waren da — nur der Befehl fehlte.
ADRs waren damit die einzige der vier dokumentierten Dokumentarten, die sich
nicht anlegen liess.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tool"))

_ROOT = Path(__file__).resolve().parents[2]


def _project(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, capture_output=True)
    subprocess.run(["sdd", "init", "--name", "P"], cwd=tmp_path,
                   capture_output=True, timeout=180)
    return tmp_path


def _adr(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["sdd", "new", "adr", *args], cwd=root,
                          capture_output=True, text=True, timeout=120)


def _fm(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8").split("---")[1])


class TestCommandExists:
    def test_template_is_registered(self):
        from sdd_cli.templates import TEMPLATE_MAP
        assert "adr" in TEMPLATE_MAP, "Die ausgelieferte Vorlage war nicht aufloesbar"

    def test_adr_is_a_known_id_kind(self):
        """ids.search_dirs() warf fuer 'adr' ein ValueError."""
        from sdd_cli.ids import KINDS, search_dirs
        from sdd_cli.config import SddConfig
        assert "adr" in KINDS
        cfg = SddConfig(root=Path("/tmp"), raw={})
        assert search_dirs(cfg, "adr") == [Path("/tmp/docs/adr")]

    def test_output_dir_is_configurable(self):
        from sdd_cli.config import SddConfig
        cfg = SddConfig(root=Path("/tmp"), raw={"adr": {"output_dir": "beschluesse"}})
        assert cfg.adr_dir == Path("/tmp/beschluesse")


class TestCreatesAdr:
    def test_creates_file_in_docs_adr(self, tmp_path):
        root = _project(tmp_path)
        result = _adr(root, "SQLite als Persistenz")
        assert result.returncode == 0, result.stdout + result.stderr
        files = list((root / "docs" / "adr").glob("ADR-*.md"))
        assert len(files) == 1, f"gefunden: {files}"
        assert files[0].name.startswith("ADR-0001-")

    def test_ids_increment(self, tmp_path):
        root = _project(tmp_path)
        _adr(root, "Erste")
        _adr(root, "Zweite")
        ids = sorted(_fm(f)["id"] for f in (root / "docs" / "adr").glob("ADR-*.md"))
        assert ids == ["ADR-0001", "ADR-0002"]

    def test_frontmatter_is_valid_yaml_with_filled_date(self, tmp_path):
        root = _project(tmp_path)
        _adr(root, "Beispiel")
        fm = _fm(next((root / "docs" / "adr").glob("ADR-*.md")))
        assert fm["status"] == "proposed"
        assert fm["date"] != "YYYY-MM-DD", "date-Platzhalter blieb stehen"
        assert fm["title"] == "Beispiel"

    def test_spec_and_supersedes_are_recorded(self, tmp_path):
        root = _project(tmp_path)
        _adr(root, "Erste")
        _adr(root, "Zweite", "--spec", "SPEC-0001", "--spec", "SPEC-0002",
             "--supersedes", "ADR-0001")
        second = next(f for f in (root / "docs" / "adr").glob("ADR-*.md")
                      if _fm(f)["id"] == "ADR-0002")
        fm = _fm(second)
        assert fm["related_specs"] == ["SPEC-0001", "SPEC-0002"]
        assert fm["supersedes"] == "ADR-0001"

    def test_body_keeps_the_decision_sections(self, tmp_path):
        root = _project(tmp_path)
        _adr(root, "Beispiel")
        body = next((root / "docs" / "adr").glob("ADR-*.md")).read_text(encoding="utf-8")
        for heading in ("## Kontext", "## Optionen", "## Entscheidung", "## Konsequenzen"):
            assert heading in body, f"{heading} fehlt"
