"""SPEC-0054 FR-09: LLM-Judge mit versionierter Rubrik, standardmäßig ohne Gewicht."""
from __future__ import annotations

import pytest

from sdd_cli.llm.base import CompletionResult
from sdd_cli.quality.judge import DEFAULT_RUBRIC_VERSION, judge_node


class _Fake:
    def __init__(self, text):
        self.text = text
        self.prompts = []

    def complete(self, prompt, **_kw):
        self.prompts.append(prompt)
        return CompletionResult(text=self.text)


def test_bewertung_und_normierung(tmp_path):
    fake = _Fake('Antwort: {"scores": {"lesbarkeit": 5, "idiomatik": 3, "passung": 1, '
                 '"fehlerbehandlung": 3}}')
    node = judge_node(tmp_path, "diff --git a/x b/x\n+neu", fake, "fake-model", weight=0.0)
    assert node.score() == pytest.approx(0.5)
    assert node.weight == 0.0
    assert node.extra == {"model": "fake-model", "rubric_version": DEFAULT_RUBRIC_VERSION}
    assert "+neu" in fake.prompts[0]


def test_versionierte_rubrik_aus_projekt(tmp_path):
    (tmp_path / ".sdd/roles").mkdir(parents=True)
    (tmp_path / ".sdd/roles/judge.md").write_text("---\nrole: judge\nversion: 2.1.0\n---\nMeine Rubrik\n")
    fake = _Fake('{"scores": {"a": 5}}')
    node = judge_node(tmp_path, "d", fake, "m", weight=0.0)
    assert node.extra["rubric_version"] == "2.1.0" and "Meine Rubrik" in fake.prompts[0]


@pytest.mark.parametrize(("diff", "antwort", "grund"), [
    ("", '{"scores": {"a": 5}}', "kein Diff"), ("d", "kein json", "Antwort nicht auswertbar"),
    ("d", '{"scores": {"a": 9}}', "Antwort nicht auswertbar")])
def test_na_faelle(tmp_path, diff, antwort, grund):
    node = judge_node(tmp_path, diff, _Fake(antwort), "m", weight=0.0)
    assert node.score() is None and grund in node.na_reason()
