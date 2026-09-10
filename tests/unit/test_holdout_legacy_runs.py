"""Legacy-Holdouts: keine Zustandsisolierung zwischen den Laeufen.

Der Legacy-Pfad fuehrte jedes Szenario dreimal aus, ohne den Zustand
zurueckzusetzen. Szenarien, die etwas anlegen, gelingen in Lauf 1 und scheitern
in 2 und 3 an dem, was Lauf 1 hinterlassen hat — und Szenarien, die einen
Konflikt erwarten, bestehen ab Lauf 2 aus dem falschen Grund. Drei Laeufe ohne
Reset messen nicht die Stabilitaet der Implementierung, sondern die Idempotenz
des Szenarios.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tool"))

from sdd_cli.config import SddConfig

# ScenarioResult/ScenarioRun gibt es in beiden Staenden; die neuen Symbole
# werden lazy geholt, damit die Verhaltenstests auch gegen einen Stand ohne sie
# laufen und der RED-Nachweis nicht auf einen Collection-Error zusammenfaellt.
from sdd_cli.evaluator import ScenarioResult, ScenarioRun


def _runs_per_scenario(cfg):
    from sdd_cli.evaluator import _legacy_runs_per_scenario as _impl
    return _impl(cfg)


def _threshold(runs: int) -> int:
    from sdd_cli.evaluator import _majority_threshold as _impl
    return _impl(runs)


def _cfg(raw: dict | None = None) -> SddConfig:
    return SddConfig(root=Path("/tmp"), raw=raw or {})


def _run(nr: int, passed: bool) -> ScenarioRun:
    return ScenarioRun(run=nr, passed=passed, request={}, response_status=201 if passed else 409,
                       response_body="", llm_verdict="pass" if passed else "fail",
                       llm_reasoning="")


class TestRunCountIsConfigurable:
    def test_default_is_one(self):
        """Ohne Isolierung ist ein Lauf der einzige aussagekraeftige."""
        from sdd_cli.evaluator import DEFAULT_RUNS_PER_SCENARIO

        assert DEFAULT_RUNS_PER_SCENARIO == 1
        assert _runs_per_scenario(_cfg()) == 1

    def test_config_value_is_read(self):
        """Der Schluessel stand in der config.yaml und wurde nie gelesen."""
        assert _runs_per_scenario(
            _cfg({"evaluator": {"runs_per_scenario": 5}})) == 5

    def test_invalid_value_falls_back(self):
        assert _runs_per_scenario(
            _cfg({"evaluator": {"runs_per_scenario": "drei"}})) == 1

    def test_zero_is_raised_to_one(self):
        assert _runs_per_scenario(
            _cfg({"evaluator": {"runs_per_scenario": 0}})) == 1


class TestThresholdFollowsRunCount:
    def test_single_run_can_pass(self):
        """Mit PASS_THRESHOLD = 2 konnte ein Einzellauf nie bestehen."""
        assert _threshold(1) == 1

    def test_three_runs_keep_the_majority_rule(self):
        assert _threshold(3) == 2

    def test_five_runs_need_three(self):
        assert _threshold(5) == 3

    def test_single_passing_run_yields_pass(self):
        result = ScenarioResult(hol_id="HOL-0001", title="T", contract="CON-0001",
                                pass_threshold=_threshold(1))
        result.runs.append(_run(1, True))
        assert result.passed is True

    def test_single_failing_run_yields_fail(self):
        result = ScenarioResult(hol_id="HOL-0001", title="T", contract="CON-0001",
                                pass_threshold=_threshold(1))
        result.runs.append(_run(1, False))
        assert result.passed is False


class TestReportedScenarioFromTheIssue:
    """HOL-0005 aus dem Bericht: Lauf 1 pass, Laeufe 2+3 fail am Restzustand."""

    def _drei_laeufe(self) -> ScenarioResult:
        result = ScenarioResult(hol_id="HOL-0005", title="Basis-URL wird normalisiert",
                                contract="CON-0001", pass_threshold=_threshold(3))
        result.runs.append(_run(1, True))
        result.runs.append(_run(2, False))
        result.runs.append(_run(3, False))
        return result

    def test_three_runs_would_still_fail_a_correct_implementation(self):
        assert self._drei_laeufe().passed is False

    def test_one_run_reflects_the_implementation(self):
        result = ScenarioResult(hol_id="HOL-0005", title="T", contract="CON-0001",
                                pass_threshold=_threshold(1))
        result.runs.append(_run(1, True))
        assert result.passed is True

    def test_dataclass_default_alone_would_reject_a_single_run(self):
        """Warum der Legacy-Pfad den Threshold jetzt explizit uebergibt.

        Der Dataclass-Default ist unveraendert PASS_THRESHOLD = 2 und auf genau
        drei Laeufe zugeschnitten. Wer ihn bei einem Lauf stehen laesst, bekommt
        ein Szenario, das nie bestehen kann.
        """
        result = ScenarioResult(hol_id="HOL-0005", title="T", contract="CON-0001")
        result.runs.append(_run(1, True))
        assert result.passed is False
        assert _threshold(1) == 1, "deshalb der abgeleitete Threshold"

    def test_divergent_runs_are_detectable(self):
        """Das Muster, auf das der Hinweis in der Ausgabe reagiert."""
        result = self._drei_laeufe()
        assert 0 < result.pass_count < len(result.runs)
