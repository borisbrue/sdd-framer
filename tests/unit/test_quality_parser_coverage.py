"""SPEC-0054 FR-02/FR-08: Cobertura- und LCOV-Parser liefern die Metrik coverage."""
from __future__ import annotations

import pytest

from sdd_cli.quality.parsers import ParseError, parse_output


def _parse(tmp_path, fmt, text):
    datei = tmp_path / "cov"
    datei.write_text(text, encoding="utf-8")
    return {m.name: m.value for m in parse_output(fmt, datei, tmp_path).metrics}


def test_cobertura_mit_zeilenzahlen(tmp_path):
    xml = '<coverage lines-valid="200" lines-covered="150" line-rate="0.1"/>'
    assert _parse(tmp_path, "cobertura", xml) == {"coverage": 0.75}


def test_cobertura_nur_line_rate(tmp_path):
    assert _parse(tmp_path, "cobertura", '<coverage line-rate="0.5"/>') == {"coverage": 0.5}


def test_lcov_summiert_ueber_dateien(tmp_path):
    text = "SF:a.py\nLF:10\nLH:5\nend_of_record\nSF:b.py\nLF:30\nLH:25\nend_of_record\n"
    assert _parse(tmp_path, "lcov", text) == {"coverage": 0.75}


@pytest.mark.parametrize(("fmt", "text"), [("cobertura", "<coverage/>"), ("cobertura", "x"),
                                           ("lcov", "SF:a.py\nend_of_record\n")])
def test_ungueltig(tmp_path, fmt, text):
    with pytest.raises(ParseError):
        _parse(tmp_path, fmt, text)
