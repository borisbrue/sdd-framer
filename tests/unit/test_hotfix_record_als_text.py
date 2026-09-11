"""Hotfix-Records: Skalare bleiben Text, egal wie die Datei entstand (#130).

`sdd status` brach ab, wenn ein Kurzhash nur aus Ziffern bestand: yaml.safe_load
machte `commit: 2494608` zu int, und Rich rendert kein int. Der Fall trifft jeden
16. Kurzhash. Mit führender 0 und Ziffern bis 7 (`0123456`) wäre der Wert sogar
als Oktalzahl gelesen worden, ein str() hätte dann einen falschen Hash gezeigt.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from sdd_cli.hotfix import _read_hf, _write_hf, list_hotfixes, start


def _record(root: Path, **felder: str) -> Path:
    """Schreibt einen Record von Hand, ohne Quoting, wie ein Editor es täte."""
    d = root / ".sdd" / "hotfixes"
    d.mkdir(parents=True, exist_ok=True)
    werte = {"id": "HF-0038", "description": "Fix", "status": "done",
             "created": "2026-09-11", "commit": "2494608", **felder}
    pfad = d / "HF-0038.md"
    pfad.write_text("---\n" + "".join(f"{k}: {v}\n" for k, v in werte.items()) + "---\n",
                    encoding="utf-8")
    return pfad


@pytest.mark.parametrize("literal", [
    "2494608",     # int
    "0123456",     # Oktal: safe_load liefert 42798
    "0x1a2b3",     # Hex: safe_load liefert 107187
    "1e12345",     # bleibt auch bei safe_load Text; Kontrolle
])
def test_kurzhash_bleibt_woertlich_erhalten(tmp_path, literal):
    _record(tmp_path, commit=literal)
    (h,) = list_hotfixes(tmp_path)
    assert h["commit"] == literal
    assert isinstance(h["created"], str) and h["created"] == "2026-09-11"


@pytest.mark.parametrize("literal", ["null", "~", ""])
def test_offener_hotfix_hat_kein_commit(tmp_path, literal):
    _record(tmp_path, status="open", commit=literal)
    (h,) = list_hotfixes(tmp_path)
    assert h["commit"] is None


def test_vom_writer_geschriebene_records_lesen_sich_unveraendert(tmp_path):
    (tmp_path / ".sdd").mkdir()
    hf_id = start(tmp_path, "Ziffernhash")
    daten = _read_hf(tmp_path / ".sdd" / "hotfixes" / f"{hf_id}.md")
    assert daten["commit"] is None and daten["status"] == "open"

    daten.update(status="done", commit="2494608")
    pfad = tmp_path / ".sdd" / "hotfixes" / f"{hf_id}.md"
    _write_hf(pfad, daten)
    assert _read_hf(pfad) == daten


def _projekt(root: Path) -> None:
    (root / ".sdd" / "specs").mkdir(parents=True)
    (root / ".sdd" / "config.yaml").write_text("project:\n  id: PRJ-0001\n  name: T\n",
                                               encoding="utf-8")


@pytest.mark.parametrize("befehl", [["status"], ["hotfix", "list"]])
def test_cli_rendert_ziffernhash(tmp_path, monkeypatch, befehl):
    """Genau der Absturz aus #130: NotRenderableError beim Rendern der Tabelle."""
    from sdd_cli.main import cli

    _projekt(tmp_path)
    _record(tmp_path)
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(cli, befehl)
    assert result.exit_code == 0, result.output + repr(result.exception)
    assert "2494608" in result.output
