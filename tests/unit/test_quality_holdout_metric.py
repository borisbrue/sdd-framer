"""SPEC-0054 FR-04, CON-0196 (holdout_pass_rate)."""
from __future__ import annotations

import json

import pytest

from sdd_cli.quality.requirements import holdout_pass_rate


def _eval(root, name, scenarios):
    (root / ".sdd/evaluations").mkdir(parents=True, exist_ok=True)
    (root / f".sdd/evaluations/{name}.json").write_text(json.dumps({"scenarios": [
        {"contract": c, "passed": ok, "runs": [{"llm_verdict": v}] if v else []}
        for c, ok, v in scenarios]}))


def test_juengste_gueltige_datei_und_zaehlung(tmp_path):
    _eval(tmp_path, "2026-01-01T00-00-00", [("CON-1", True, "")])
    _eval(tmp_path, "2026-02-01T00-00-00", [("CON-1", True, ""), ("CON-1", False, ""),
                                           ("CON-1", False, "skip"), ("CON-1", False, "error"),
                                           ("CON-9", False, "")])
    assert holdout_pass_rate(tmp_path, ["CON-1"]) == pytest.approx(0.5)


def test_datei_nur_mit_messfehlern_wird_uebersprungen(tmp_path):
    _eval(tmp_path, "2026-01-01T00-00-00", [("CON-1", True, "")])
    _eval(tmp_path, "2026-02-01T00-00-00", [("CON-1", False, "error")])
    assert holdout_pass_rate(tmp_path, ["CON-1"]) == pytest.approx(1.0)


def test_ohne_passende_datei(tmp_path):
    assert holdout_pass_rate(tmp_path, ["CON-1"]) is None
    _eval(tmp_path, "x", [("CON-9", True, "")])
    assert holdout_pass_rate(tmp_path, ["CON-1"]) is None
    assert holdout_pass_rate(tmp_path, []) is None


def test_kaputte_datei_wird_ignoriert(tmp_path):
    (tmp_path / ".sdd/evaluations").mkdir(parents=True)
    (tmp_path / ".sdd/evaluations/z.json").write_text("{")
    _eval(tmp_path, "a", [("CON-1", True, "")])
    assert holdout_pass_rate(tmp_path, ["CON-1"]) == pytest.approx(1.0)
