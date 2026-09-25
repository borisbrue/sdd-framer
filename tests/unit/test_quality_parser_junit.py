"""SPEC-0054 FR-02/FR-03, CON-0193 INV-09: JUnit-Parser."""
from __future__ import annotations

import pytest

from sdd_cli.quality.parsers import ParseError, parse_output

XML = """<?xml version="1.0"?>
<testsuites><testsuite name="s">
  <testcase classname="tests.a" name="test_ok" file="tests/a.py">
    <properties><property name="fr" value="FR-01"/><property name="fr" value="FR-02"/></properties>
  </testcase>
  <testcase classname="tests.a" name="test_rot"><failure message="x">boom</failure></testcase>
  <testcase classname="tests.a" name="test_kaputt"><error message="e"/></testcase>
  <testcase classname="tests.a" name="test_weg"><skipped/></testcase>
  <testcase classname="tests.b" name="test_FR-07_im_namen"/>
</testsuite></testsuites>"""


def _parse(tmp_path, text, **opt):
    datei = tmp_path / "out.xml"
    datei.write_text(text, encoding="utf-8")
    return parse_output("junit", datei, tmp_path, **opt)


def test_status_und_fr_properties(tmp_path):
    faelle = {c.name: c for c in _parse(tmp_path, XML, fr_marker="property").cases}
    assert faelle["test_ok"].status == "passed"
    assert faelle["test_ok"].frs == ("FR-01", "FR-02")
    assert faelle["test_ok"].file == "tests/a.py"
    assert faelle["test_rot"].status == "failed"
    assert faelle["test_kaputt"].status == "error"
    assert faelle["test_weg"].status == "skipped"
    assert faelle["test_FR-07_im_namen"].frs == ()


def test_fr_im_namen(tmp_path):
    faelle = {c.name: c for c in _parse(tmp_path, XML, fr_marker="name").cases}
    assert faelle["test_FR-07_im_namen"].frs == ("FR-07",)
    assert faelle["test_ok"].frs == ()


def test_einzelne_testsuite_als_wurzel(tmp_path):
    xml = '<testsuite><testcase classname="c" name="t"/></testsuite>'
    assert [c.name for c in _parse(tmp_path, xml).cases] == ["t"]


@pytest.mark.parametrize("text", ["kein xml", "<andere/>", "<testsuite><testcase/></testsuite>"])
def test_ungueltig(tmp_path, text):
    with pytest.raises(ParseError):
        _parse(tmp_path, text)
