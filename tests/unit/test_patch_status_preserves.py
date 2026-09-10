"""patch_status darf nur die Statuszeile anfassen.

Frueher lief es ueber parse() -> frontmatter["status"] = ... -> write(), also
einen vollstaendigen YAML-Roundtrip. Der schrieb das gesamte Frontmatter neu und
verlor alle Inline-Kommentare, die Quotes um Strings und die Leerzeile nach dem
schliessenden ---.

Zwei Folgen: die Frontmatter-Dokumentation verschwand bei jedem Statuswechsel,
und der Content-Hash aenderte sich, obwohl compute_content_hash die
status:-Zeile ausdruecklich herausfiltert — der pre-commit-Hook stufte den
gerade gesetzten Status daraufhin zurueck ("implemented -> review").
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tool"))

from sdd_cli.frontmatter import parse, patch_status
from sdd_cli.lifecycle import compute_content_hash

_MIT_KOMMENTAREN = '''---
id: HOL-0001
title: "<Szenario-Name>"
spec: SPEC-0001
contract: CON-0001
status: ready            # ready | active | disabled | wip
                         # ready und active werden evaluiert, wip und disabled nicht
priority: normal         # critical | normal | edge-case
tags: []
---

# Holdout

Inhalt.
'''


def _datei(tmp_path: Path, text: str = _MIT_KOMMENTAREN) -> Path:
    p = tmp_path / "doc.md"
    p.write_text(text, encoding="utf-8")
    return p


class TestNurDieStatuszeileAendertSich:
    def test_status_wird_gesetzt(self, tmp_path):
        p = _datei(tmp_path)
        patch_status(p, "active")
        assert parse(p).frontmatter["status"] == "active"

    def test_inline_kommentare_bleiben(self, tmp_path):
        p = _datei(tmp_path)
        patch_status(p, "active")
        text = p.read_text(encoding="utf-8")
        assert "# critical | normal | edge-case" in text
        assert "ready und active werden evaluiert" in text

    def test_kommentar_hinter_dem_status_bleibt(self, tmp_path):
        p = _datei(tmp_path)
        patch_status(p, "active")
        assert "# ready | active | disabled | wip" in p.read_text(encoding="utf-8")

    def test_quotes_bleiben(self, tmp_path):
        p = _datei(tmp_path)
        patch_status(p, "active")
        assert 'title: "<Szenario-Name>"' in p.read_text(encoding="utf-8")

    def test_leerzeile_nach_dem_frontmatter_bleibt(self, tmp_path):
        p = _datei(tmp_path)
        patch_status(p, "active")
        assert "---\n\n# Holdout" in p.read_text(encoding="utf-8")

    def test_genau_eine_zeile_unterscheidet_sich(self, tmp_path):
        p = _datei(tmp_path)
        vor = p.read_text(encoding="utf-8").splitlines()
        patch_status(p, "active")
        nach = p.read_text(encoding="utf-8").splitlines()
        assert len(vor) == len(nach)
        unterschiede = [i for i, (a, b) in enumerate(zip(vor, nach, strict=True)) if a != b]
        assert len(unterschiede) == 1, f"geaendert: {unterschiede}"


class TestHashBleibtStabil:
    """Der Kern des gemeldeten Fehlers."""

    def test_hash_aendert_sich_nicht(self, tmp_path):
        p = _datei(tmp_path)
        vorher = compute_content_hash(p.read_text(encoding="utf-8"))
        patch_status(p, "implemented")
        assert compute_content_hash(p.read_text(encoding="utf-8")) == vorher

    def test_auch_bei_mehreren_wechseln(self, tmp_path):
        p = _datei(tmp_path)
        vorher = compute_content_hash(p.read_text(encoding="utf-8"))
        for status in ("active", "wip", "implemented", "review"):
            patch_status(p, status)
            assert compute_content_hash(p.read_text(encoding="utf-8")) == vorher, status


class TestRandfaelle:
    def test_ohne_frontmatter_passiert_nichts(self, tmp_path):
        p = tmp_path / "doc.md"
        p.write_text("# Nur Text\n", encoding="utf-8")
        patch_status(p, "active")
        assert p.read_text(encoding="utf-8") == "# Nur Text\n"

    def test_fehlendes_statusfeld_wird_ergaenzt(self, tmp_path):
        p = _datei(tmp_path, "---\nid: SPEC-0001\ntitle: T\n---\n\n# X\n")
        patch_status(p, "approved")
        assert parse(p).frontmatter["status"] == "approved"

    def test_body_bleibt_unangetastet(self, tmp_path):
        p = _datei(tmp_path)
        vorher = p.read_text(encoding="utf-8").split("---\n", 2)[2]
        patch_status(p, "active")
        assert p.read_text(encoding="utf-8").split("---\n", 2)[2] == vorher

    def test_status_im_body_wird_nicht_getroffen(self, tmp_path):
        """Der Regex arbeitet nur im Frontmatter-Block."""
        p = _datei(tmp_path, "---\nid: X\nstatus: draft\n---\n\nstatus: draft\n")
        patch_status(p, "approved")
        text = p.read_text(encoding="utf-8")
        assert text.count("status: approved") == 1
        assert text.endswith("status: draft\n")
