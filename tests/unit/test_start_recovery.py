"""Nach einem gescheiterten `finalize` muss es einen Weg zurueck geben.

`sdd finalize` entfernte den Dev-Container, **bevor** es scheitern konnte. Beim
zweiten Anlauf:

    ✗ Dev-Container nicht gefunden – starte ihn mit 'sdd start SPEC-0005'

`sdd start` antwortete aber "SPEC-0005 ist bereits in-progress." und tat nichts.
`sdd dev` gibt es seit SPEC-0044 nicht mehr. Der einzige Ausweg war, den
Container von Hand nachzubauen.
"""
from __future__ import annotations

import inspect
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tool"))

from sdd_cli.config import SddConfig
from sdd_cli.lifecycle import start_spec


def _projekt(tmp_path: Path, status: str) -> SddConfig:
    (tmp_path / ".sdd" / "specs").mkdir(parents=True)
    (tmp_path / ".sdd" / "specs" / "SPEC-0001-demo.md").write_text(
        f"---\nid: SPEC-0001\ntitle: Demo\nstatus: {status}\nowner: B\n"
        f"version: 0.1.0\ntests: []\n---\n\n# Demo\n", encoding="utf-8")
    return SddConfig(root=tmp_path, raw={})


class TestErneuterStartIstMoeglich:
    def test_in_progress_wirft_nicht_mehr(self, tmp_path):
        """Der gemeldete Fall: `sdd start` kehrte kommentarlos zurueck."""
        result = start_spec(_projekt(tmp_path, "in-progress"), "SPEC-0001")
        assert result.spec_id == "SPEC-0001"

    def test_status_bleibt_unveraendert(self, tmp_path):
        from sdd_cli.frontmatter import parse

        cfg = _projekt(tmp_path, "in-progress")
        start_spec(cfg, "SPEC-0001")
        doc = parse(cfg.root / ".sdd" / "specs" / "SPEC-0001-demo.md")
        assert doc.frontmatter["status"] == "in-progress"

    def test_ergebnis_meldet_den_unveraenderten_status(self, tmp_path):
        result = start_spec(_projekt(tmp_path, "in-progress"), "SPEC-0001")
        assert result.status_changed is False

    def test_kein_audit_eintrag_beim_zweiten_start(self, tmp_path):
        cfg = _projekt(tmp_path, "in-progress")
        start_spec(cfg, "SPEC-0001")
        audit = cfg.root / ".sdd" / "audit.log"
        assert not audit.exists() or "in-progress" not in audit.read_text(encoding="utf-8")


class TestErstStartVerhaeltSichUnveraendert:
    def test_approved_wird_uebernommen(self, tmp_path):
        from sdd_cli.frontmatter import parse

        cfg = _projekt(tmp_path, "approved")
        result = start_spec(cfg, "SPEC-0001")
        doc = parse(cfg.root / ".sdd" / "specs" / "SPEC-0001-demo.md")
        assert result.status_changed is True
        assert doc.frontmatter["status"] == "in-progress"

    def test_draft_wird_weiter_abgelehnt(self, tmp_path):
        """Das Execution Gate bleibt wirksam."""
        with pytest.raises(ValueError, match="Execution Gate"):
            start_spec(_projekt(tmp_path, "draft"), "SPEC-0001")


class TestContainerUeberlebtDenFehlschlag:
    def test_close_nur_bei_gruenen_tests(self):
        from sdd_cli.finalize import SpecFinalizer

        src = inspect.getsource(SpecFinalizer.run)
        assert "if not compose_file and tests_passed:" in src, (
            "Der Container wird weiterhin vor dem moeglichen Fehlschlag entfernt"
        )
