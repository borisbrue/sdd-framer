"""Holdouts duerfen nicht still aus der Evaluation fallen.

`sdd new holdout` erzeugte `status: wip`. evaluator._EVAL_STATUSES kennt nur
{"active", "ready"} — das Szenario wurde also kommentarlos herausgefiltert.
SPEC-0033 FR-03 schreibt `status: ready` vor; die Templates setzten ihn nur
nicht. Wer der Vorlage folgte, bekam null evaluierte Szenarien ohne Hinweis.
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tool"))

from sdd_cli.config import load_config

_TEMPLATE_DIRS = [
    Path(__file__).resolve().parents[2] / "tool" / "sdd_cli" / "blueprint" / "templates" / "holdout",
    Path(__file__).resolve().parents[2] / ".sdd" / "templates" / "holdout",
]


def _templates():
    for d in _TEMPLATE_DIRS:
        yield from sorted(d.glob("*.md"))


class TestTemplatesAreEvaluable:
    """FR-03 nennt `status: ready`. Die Templates schrieben `wip`."""

    def test_every_template_status_is_evaluated(self):
        from sdd_cli.evaluator import _EVAL_STATUSES

        for tmpl in _templates():
            fm = yaml.safe_load(tmpl.read_text(encoding="utf-8").split("---")[1])
            assert fm["status"] in _EVAL_STATUSES, (
                f"{tmpl}: status {fm['status']!r} wird vom Evaluator herausgefiltert — "
                f"das Szenario faellt still aus der Auswertung."
            )

    def test_spec_0033_prescribes_ready(self):
        for tmpl in _templates():
            fm = yaml.safe_load(tmpl.read_text(encoding="utf-8").split("---")[1])
            assert fm["status"] == "ready", f"{tmpl}: SPEC-0033 FR-03 nennt 'ready'"

    def test_templates_exist_in_both_places(self):
        for d in _TEMPLATE_DIRS:
            assert list(d.glob("*.md")), f"Keine Templates in {d}"


class TestSkippedScenariosAreCounted:
    def _load(self, cfg):
        from sdd_cli.evaluator import _load_holdout_docs_with_skips
        return _load_holdout_docs_with_skips(cfg)

    def _project(self, tmp_path: Path, *statuses: str) -> Path:
        (tmp_path / ".sdd" / "holdout").mkdir(parents=True)
        (tmp_path / ".sdd" / "config.yaml").write_text("version: 1\n", encoding="utf-8")
        for i, status in enumerate(statuses, start=1):
            (tmp_path / ".sdd" / "holdout" / f"HOL-{i:04d}-x.md").write_text(
                f"---\nid: HOL-{i:04d}\ntitle: X\nspec: SPEC-0001\n"
                f"contract: CON-0001\nstatus: {status}\n---\n\n# X\n", encoding="utf-8")
        return tmp_path

    def test_wip_scenarios_are_counted_not_swallowed(self, tmp_path):
        cfg = load_config(self._project(tmp_path, "wip", "wip", "ready"))
        docs, skipped = self._load(cfg)
        assert len(docs) == 1
        assert skipped == {"wip": 2}

    def test_all_skipped_yields_empty_run_with_reason(self, tmp_path):
        """Der gemeldete Fall: 12 Szenarien angelegt, null evaluiert."""
        cfg = load_config(self._project(tmp_path, *(["wip"] * 12)))
        docs, skipped = self._load(cfg)
        assert docs == []
        assert sum(skipped.values()) == 12, "Ein leerer Lauf muss seinen Grund kennen"

    def test_disabled_is_counted_separately(self, tmp_path):
        cfg = load_config(self._project(tmp_path, "wip", "disabled", "active"))
        _, skipped = self._load(cfg)
        assert skipped == {"wip": 1, "disabled": 1}

    def test_nothing_skipped_when_all_evaluable(self, tmp_path):
        cfg = load_config(self._project(tmp_path, "ready", "active"))
        docs, skipped = self._load(cfg)
        assert len(docs) == 2 and skipped == {}

    def test_report_carries_the_count(self):
        from sdd_cli.evaluator import EvaluationReport
        rep = EvaluationReport(timestamp="t", base_url="u", skipped_by_status={"wip": 3})
        assert rep.to_dict()["summary"]["skipped_by_status"] == {"wip": 3}
