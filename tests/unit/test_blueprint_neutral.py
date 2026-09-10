"""Das Blueprint liefert keine Werte aus dieser einen Umgebung aus (#116).

`sdd init` kopierte `owners: [Boris]` und den Obsidian-Vault-Pfad eines anderen
Rechners (`/home/deck/…`) in jedes neue Projekt — dieselbe Klasse wie der feste
PWA-Token in #69. Den Wert fing test_blueprint_geheimnisse.py nicht, weil er
nicht nach Geheimnis aussah.
"""
from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

_ROOT = Path(__file__).resolve().parents[2]
_BLUEPRINT = _ROOT / "tool" / "sdd_cli" / "blueprint" / "config.yaml"

# Absolute Pfade in ein Benutzerverzeichnis oder auf ein Wechselmedium.
_HEIMATPFAD = re.compile(r"^(?:/home/|/Users/|/run/media/|/media/|[A-Za-z]:\\\\Users\\\\)")


def _werte(knoten, pfad=""):
    if isinstance(knoten, dict):
        for k, v in knoten.items():
            yield from _werte(v, f"{pfad}.{k}" if pfad else str(k))
    elif isinstance(knoten, list):
        for i, v in enumerate(knoten):
            yield from _werte(v, f"{pfad}[{i}]")
    else:
        yield pfad, knoten


@pytest.fixture(scope="module")
def blueprint():
    return yaml.safe_load(_BLUEPRINT.read_text(encoding="utf-8"))


class TestBlueprint:
    def test_keine_heimatpfade(self, blueprint):
        treffer = [f"{p} = {w}" for p, w in _werte(blueprint)
                   if isinstance(w, str) and _HEIMATPFAD.match(w)]
        assert not treffer, "rechnerspezifische Pfade im Blueprint: " + "; ".join(treffer)

    def test_keine_owner_vorbelegt(self, blueprint):
        assert blueprint["project"]["owners"] == []

    def test_obsidian_aus_bis_ein_vault_gesetzt_ist(self, blueprint):
        assert blueprint["obsidian"]["vault_path"] == ""

    def test_projektname_ist_platzhalter(self, blueprint):
        assert blueprint["project"]["name"] == "<PROJECT_TITLE>"


def _init(tmp_path, git_name):
    from sdd_cli import init as init_mod

    with patch.object(init_mod, "_git_benutzername", return_value=git_name):
        init_mod.init_project(tmp_path, title="Fremdes Projekt")
    return yaml.safe_load((tmp_path / ".sdd" / "config.yaml").read_text(encoding="utf-8"))


class TestInit:
    def test_owner_kommt_aus_git(self, tmp_path):
        assert _init(tmp_path, "Ada Lovelace")["project"]["owners"] == ["Ada Lovelace"]

    def test_owner_mit_sonderzeichen_bleibt_gueltiges_yaml(self, tmp_path):
        name = "O'Brien: Test #1"
        assert _init(tmp_path, name)["project"]["owners"] == [name]

    def test_ohne_git_name_bleibt_die_liste_leer(self, tmp_path):
        assert _init(tmp_path, None)["project"]["owners"] == []

    def test_projektname_wird_eingesetzt(self, tmp_path):
        assert _init(tmp_path, None)["project"]["name"] == "Fremdes Projekt"

    def test_kein_fremder_wert_im_neuen_projekt(self, tmp_path):
        _init(tmp_path, "Ada Lovelace")
        text = (tmp_path / ".sdd" / "config.yaml").read_text(encoding="utf-8")
        for fremd in ("Boris", "/home/deck", "Vault 33", "SDD Framer"):
            assert fremd not in text, f"{fremd!r} im erzeugten Projekt"

    def test_obsidian_meldet_den_dokumentierten_fehler(self, tmp_path):
        """SPEC-0009: ohne vault_path kommt "obsidian.vault_path nicht konfiguriert"."""
        from sdd_cli.config import load_config
        from sdd_cli.obsidian import export

        _init(tmp_path, None)
        with pytest.raises(ValueError, match="vault_path nicht konfiguriert"):
            export(load_config(tmp_path))


def test_git_benutzername_ohne_git():
    from sdd_cli import init as init_mod

    with patch.object(init_mod.subprocess, "run", side_effect=FileNotFoundError):
        assert init_mod._git_benutzername(Path(".")) is None
