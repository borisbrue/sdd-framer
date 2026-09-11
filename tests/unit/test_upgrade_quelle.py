"""`sdd upgrade` nimmt das Paket-Blueprint als Quelle (#126).

Bis dahin las upgrade das .sdd/ des sdd-framer-Repos: `PACKAGE_ROOT.parent.parent`
ist bei editierbarer Installation die Repo-Wurzel. Fremde Projekte bekamen so die
Repo-Config untergemischt (docker.runtime: podman, hub, title) und Templates aus
einer veralteten Kopie. Kein Test rief upgrade_project auf, TST-0197 prüfte nur
`--help`.
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


def _config(ziel: Path) -> dict:
    return yaml.safe_load((ziel / ".sdd" / "config.yaml").read_text(encoding="utf-8"))


def test_repo_config_gelangt_nicht_ins_projekt(tmp_path):
    ziel = _projekt(tmp_path, {"project": {"name": "Fremd"}, "docker": {"image": "x:1"}})
    upgrade.upgrade_project(ziel)
    cfg = _config(ziel)
    # Das Blueprint lässt runtime bewusst auskommentiert, damit es neutral bleibt.
    assert "runtime" not in cfg["docker"]
    assert "hub" not in cfg and "title" not in cfg
    assert cfg["project"]["name"] == "Fremd"
    assert cfg["docker"]["image"] == "x:1"


def test_ergaenzt_genau_die_schluessel_des_blueprints(tmp_path):
    ziel = _projekt(tmp_path)
    upgrade.upgrade_project(ziel)
    blueprint = yaml.safe_load((_blueprint_root() / "config.yaml").read_text(encoding="utf-8"))
    assert set(_config(ziel)) == set(blueprint)


@pytest.mark.parametrize("sub", ["templates", "schemas"])
def test_dateien_kommen_aus_dem_paket_blueprint(tmp_path, sub):
    ziel = _projekt(tmp_path)
    upgrade.upgrade_project(ziel)
    quelle, kopie = _blueprint_root() / sub, ziel / ".sdd" / sub

    fehlend_oder_anders = [
        str(d.relative_to(quelle)) for d in quelle.rglob("*")
        if d.is_file() and (
            not (kopie / d.relative_to(quelle)).is_file()
            or (kopie / d.relative_to(quelle)).read_bytes() != d.read_bytes()
        )
    ]
    fremd = [
        str(k.relative_to(kopie)) for k in kopie.rglob("*")
        if k.is_file() and not (quelle / k.relative_to(kopie)).is_file()
    ]
    assert not fehlend_oder_anders, fehlend_oder_anders
    assert not fremd, fremd


def test_quelle_ist_dasselbe_blueprint_wie_fuer_init(tmp_path, monkeypatch):
    """Mit einem eigenen Blueprint-Verzeichnis: upgrade liest, was init liest."""
    bp = tmp_path / "bp"
    (bp / "templates").mkdir(parents=True)
    (bp / "schemas").mkdir()
    (bp / "templates" / "nur-hier.md").write_text("x", encoding="utf-8")
    (bp / "schemas" / "s.json").write_text("{}", encoding="utf-8")
    (bp / "config.yaml").write_text("neu:\n  a: 1\n", encoding="utf-8")
    monkeypatch.setattr("sdd_cli.init._blueprint_root", lambda: bp)

    ziel = _projekt(tmp_path / "p")
    upgrade.upgrade_project(ziel)
    assert (ziel / ".sdd" / "templates" / "nur-hier.md").is_file()
    assert (ziel / ".sdd" / "schemas" / "s.json").is_file()
    assert _config(ziel)["neu"] == {"a": 1}


def test_fehlendes_blueprint_ist_ein_fehler_kein_stilles_nichts(tmp_path, monkeypatch):
    """Im Wheel zeigte der alte Pfad ins Leere, und upgrade meldete trotzdem Erfolg."""
    monkeypatch.setattr("sdd_cli.init._blueprint_root", lambda: tmp_path / "gibt-es-nicht")
    with pytest.raises(FileNotFoundError, match="Paket-Blueprint"):
        upgrade.upgrade_project(_projekt(tmp_path / "p"))


def test_eigene_templates_bleiben_schemas_werden_erneuert(tmp_path):
    ziel = _projekt(tmp_path)
    eigen = ziel / ".sdd" / "templates" / "spec" / "default.md"
    eigen.parent.mkdir(parents=True)
    eigen.write_text("meins", encoding="utf-8")
    schema = ziel / ".sdd" / "schemas" / "spec-frontmatter.schema.json"
    schema.parent.mkdir(parents=True)
    schema.write_text("{}", encoding="utf-8")

    upgrade.upgrade_project(ziel)
    assert eigen.read_text(encoding="utf-8") == "meins"
    assert schema.read_bytes() == (
        _blueprint_root() / "schemas" / "spec-frontmatter.schema.json").read_bytes()
