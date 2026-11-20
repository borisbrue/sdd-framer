"""Review findings with `line: null` stay valid (hotfix): the null is dropped, not the answer."""
from __future__ import annotations

from tool.sdd_cli.pipeline.roles import load_blueprint_role
from tool.sdd_cli.pipeline.runner import RoleRunner, drop_null_finding_lines


def _review(line):
    finding = {"category": "quality", "file": "src/a.c", "reason": "x"}
    if line != "absent":
        finding["line"] = line
    return {"verdict": "fail", "findings": [finding]}


def test_null_line_is_dropped():
    out = _review(None)
    drop_null_finding_lines(out)
    assert out["findings"] == [{"category": "quality", "file": "src/a.c", "reason": "x"}]


def test_integer_line_is_kept():
    out = _review(7)
    drop_null_finding_lines(out)
    assert out["findings"][0]["line"] == 7


def test_non_review_output_is_untouched():
    for out in (None, [], {"tasks": []}, {"findings": "x"}):
        drop_null_finding_lines(out)


def test_reviewer_schema_accepts_null_line_after_drop():
    role = load_blueprint_role("reviewer")
    probleme, _ = RoleRunner.validate_checks(role, _review(None), {})
    assert not [p for p in probleme if "line" in p]


def test_reviewer_schema_still_rejects_bad_line():
    role = load_blueprint_role("reviewer")
    probleme, gescheitert = RoleRunner.validate_checks(role, _review(0), {})
    assert gescheitert == ["json_schema"] and any("line" in p for p in probleme)
