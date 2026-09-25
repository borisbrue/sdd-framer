"""SPEC-0054 FR-07 (arch init): Schichtvorschlag aus der Verzeichnisstruktur."""
from __future__ import annotations

from sdd_cli.quality.arch.init import suggest_architecture


def test_eine_schicht_je_top_level_paket(tmp_path):
    for d in ("alpha", "beta", ".git", ".sdd", "node_modules", "docs"):
        (tmp_path / d).mkdir()
    (tmp_path / "alpha/a.py").write_text("x")
    (tmp_path / "beta/b.go").write_text("x")
    (tmp_path / "docs/readme.md").write_text("x")
    (tmp_path / "leer").mkdir()
    vorschlag = suggest_architecture(tmp_path)
    assert vorschlag == {"version": 1, "layers": {"alpha": ["alpha/**"], "beta": ["beta/**"],
                                                  "docs": ["docs/**"]}, "rules": []}


def test_schichtname_wird_bereinigt(tmp_path):
    (tmp_path / "My-Pkg").mkdir()
    (tmp_path / "My-Pkg/x.py").write_text("x")
    assert list(suggest_architecture(tmp_path)["layers"]) == ["my-pkg"]
