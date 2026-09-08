"""`sdd start` darf Platzhalter nicht als angelegte Tests melden.

start_spec() verwarf den Rueckgabewert von _implement_test_stub(). Scheiterte
die LLM-Generierung, blieb das Geruest mit `raise NotImplementedError` liegen —
und die Ausgabe meldete den Test trotzdem als angelegt, mit Exit 0. Dazu
schluckte `except Exception: pass` jede Ursache.

Ein `raise NotImplementedError` wird nie gruen. Wer der Anleitung folgt, sucht
den Fehler in seiner Implementierung statt in der Testdatei.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tool"))

from sdd_cli.config import SddConfig
# Lazy in den Tests: sonst scheitert schon das Einsammeln des Moduls
# gegen einen Stand ohne StubOutcome, und der RED-Nachweis waere
# nur ein ImportError statt eines Verhaltensbelegs.
from sdd_cli.lifecycle import start_spec


def _projekt(tmp_path: Path, raw: dict | None = None) -> SddConfig:
    (tmp_path / ".sdd" / "specs").mkdir(parents=True)
    (tmp_path / ".sdd" / "tests" / "unit").mkdir(parents=True)
    (tmp_path / ".sdd" / "specs" / "SPEC-0001-demo.md").write_text(
        "---\nid: SPEC-0001\ntitle: Demo\nstatus: approved\nowner: B\n"
        "version: 0.1.0\ntests:\n- TST-0001\n---\n\n# Demo\n", encoding="utf-8")
    (tmp_path / ".sdd" / "tests" / "unit" / "TST-0001-x.md").write_text(
        "---\nid: TST-0001\ntitle: T\nlevel: unit\nspec: SPEC-0001\n"
        'contract: CON-0001\nartifact: "tests/unit/test_x.py"\n---\n\n# T\n',
        encoding="utf-8")
    return SddConfig(root=tmp_path, raw=raw or {})


class TestFailureIsVisible:
    def test_failed_generation_is_marked_as_placeholder(self, tmp_path):
        cfg = _projekt(tmp_path)
        with patch("sdd_cli.lifecycle._implement_test_stub",
                   return_value=(False, "TimeoutError: nach 300s")):
            result = start_spec(cfg, "SPEC-0001")

        assert len(result.stubs_placeholder) == 1
        assert result.stubs_generated == []
        assert "TimeoutError" in result.stubs_placeholder[0].reason

    def test_successful_generation_is_marked_as_generated(self, tmp_path):
        cfg = _projekt(tmp_path)
        with patch("sdd_cli.lifecycle._implement_test_stub", return_value=(True, "")):
            result = start_spec(cfg, "SPEC-0001")

        assert len(result.stubs_generated) == 1
        assert result.stubs_placeholder == []

    def test_both_cases_are_distinguishable(self, tmp_path):
        """Der Kern: vorher standen beide ununterscheidbar in stubs_created."""
        cfg = _projekt(tmp_path)
        with patch("sdd_cli.lifecycle._implement_test_stub",
                   return_value=(False, "irgendein Grund")):
            result = start_spec(cfg, "SPEC-0001")

        assert len(result.stubs_created) == 1, "stubs_created bleibt rueckwaertskompatibel"
        assert result.stubs_created != result.stubs_generated

    def test_outcome_carries_the_tst_id(self, tmp_path):
        cfg = _projekt(tmp_path)
        with patch("sdd_cli.lifecycle._implement_test_stub", return_value=(False, "x")):
            result = start_spec(cfg, "SPEC-0001")
        assert result.stubs_placeholder[0].tst_id == "TST-0001"


class TestReasonIsNotSwallowed:
    def _stub_call(self, cfg: SddConfig, tmp_path: Path, provider_side_effect):
        from sdd_cli.frontmatter import parse_safe
        from sdd_cli.lifecycle import _implement_test_stub

        doc = parse_safe(tmp_path / ".sdd" / "tests" / "unit" / "TST-0001-x.md")
        target = tmp_path / "tests" / "unit" / "test_x.py"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("raise NotImplementedError\n", encoding="utf-8")
        with patch("sdd_cli.llm.factory.get_completion_provider",
                   side_effect=provider_side_effect):
            return _implement_test_stub(cfg, "TST-0001", doc, target)

    def test_exception_reason_is_returned(self, tmp_path):
        """`except Exception: pass` verbarg genau die Diagnoseinformation."""
        cfg = _projekt(tmp_path)
        ok, reason = self._stub_call(cfg, tmp_path, TimeoutError("nach 300s"))
        assert ok is False
        assert "TimeoutError" in reason and "300s" in reason

    def test_unusable_answer_gets_its_own_reason(self, tmp_path):
        cfg = _projekt(tmp_path)

        class _Result:
            text = "Hier ist dein Test!"

        class _Provider:
            def complete(self, *a, **kw):
                return _Result()

        ok, reason = self._stub_call(cfg, tmp_path, lambda *a, **kw: _Provider())
        assert ok is False
        assert "keinen pytest-Code" in reason

    def test_missing_test_doc_has_a_reason(self, tmp_path):
        from sdd_cli.lifecycle import _implement_test_stub
        ok, reason = _implement_test_stub(
            _projekt(tmp_path), "TST-0001", None, tmp_path / "x.py")
        assert ok is False and "TST-0001" in reason


class TestTimeoutIsConfigurable:
    def test_default_is_300(self, tmp_path):
        cfg = _projekt(tmp_path)
        captured = {}

        class _Provider:
            def complete(self, prompt, **kw):
                captured.update(kw)
                raise RuntimeError("abbruch")

        self_ = TestReasonIsNotSwallowed()
        self_._stub_call(cfg, tmp_path, lambda *a, **kw: _Provider())
        assert captured["timeout"] == 300

    def test_config_value_wins(self, tmp_path):
        cfg = _projekt(tmp_path, raw={"llm": {"test_generation_timeout": 900}})
        captured = {}

        class _Provider:
            def complete(self, prompt, **kw):
                captured.update(kw)
                raise RuntimeError("abbruch")

        TestReasonIsNotSwallowed()._stub_call(cfg, tmp_path, lambda *a, **kw: _Provider())
        assert captured["timeout"] == 900
