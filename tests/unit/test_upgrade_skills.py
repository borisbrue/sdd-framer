"""`sdd upgrade` rüstet fehlende Skill-Dateien nach (CON-0169, SPEC-0044 FR-06, #126).

Die Hilfe von `sdd upgrade` versprach das seit SPEC-0044. upgrade_project kopierte
aber keine einzige Skill-Datei, und TST-0197 prüfte nur das Wort in der Hilfe.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from sdd_cli import upgrade
from sdd_cli.init import _blueprint_root


def _projekt(root: Path, config: dict | None = None) -> Path:
    (root / ".sdd").mkdir(parents=True)
    (root / ".sdd" / "config.yaml").write_text(
        yaml.safe_dump(config or {"project": {"name": "Fremd"}}), encoding="utf-8")
    return root


def _claude_skills() -> list[Path]:
    return sorted((_blueprint_root() / "templates" / "agents-md" / "providers" / "claude").glob("*.md"))


def test_fehlende_skills_werden_nachgeruestet(tmp_path):
    ziel = _projekt(tmp_path)
    result = upgrade.upgrade_project(ziel)

    befehle = ziel / ".claude" / "commands"
    for skill in _claude_skills():
        assert (befehle / skill.name).read_bytes() == skill.read_bytes(), skill.name
    assert not (befehle / "settings.json").exists()
    assert sorted(p.name for p in result["skills"]) == [s.name for s in _claude_skills()]


def test_vorhandene_skills_bleiben_unberuehrt(tmp_path):
    ziel = _projekt(tmp_path)
    eigen = ziel / ".claude" / "commands" / "sdd.md"
    eigen.parent.mkdir(parents=True)
    eigen.write_text("meins", encoding="utf-8")

    result = upgrade.upgrade_project(ziel)
    assert eigen.read_text(encoding="utf-8") == "meins"
    assert eigen not in result["skills"]
    assert (ziel / ".claude" / "commands" / "sdd-implement.md").is_file()


def test_zweiter_lauf_ruestet_nichts_mehr_nach(tmp_path):
    ziel = _projekt(tmp_path)
    upgrade.upgrade_project(ziel)
    assert upgrade.upgrade_project(ziel)["skills"] == []


def test_provider_kommt_aus_der_config(tmp_path):
    """Für copilot liefert das Blueprint keine Skills. Dann entsteht auch kein .claude/."""
    ziel = _projekt(tmp_path, {"project": {"name": "Fremd"}, "skills": {"provider": "copilot"}})
    result = upgrade.upgrade_project(ziel)
    assert result["skills"] == []
    assert not (ziel / ".claude").exists()


def test_unbekannter_provider_bricht_vor_jeder_aenderung_ab(tmp_path):
    ziel = _projekt(tmp_path, {"project": {"name": "Fremd"}, "skills": {"provider": "gibtsnicht"}})
    vorher = (ziel / ".sdd" / "config.yaml").read_text(encoding="utf-8")

    with pytest.raises(ValueError, match="gibtsnicht"):
        upgrade.upgrade_project(ziel)
    assert not (ziel / ".sdd" / "schemas").exists()
    assert (ziel / ".sdd" / "config.yaml").read_text(encoding="utf-8") == vorher
