"""Die Pipeline-Trigger im Web-UI streamen ihre Logs (#112, ruff F821).

`trigger_evaluate` und `trigger_implement` riefen `sdd_context.get_log_event_bus()`
auf, ohne `sdd_context` zu importieren. Das NameError fing ein
`except Exception: pass` — der Bus blieb None, und die LogView blieb leer.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def umgebung(tmp_path):
    cfg = SimpleNamespace(root=tmp_path, raw={"evaluator": {"base_url": "http://ziel:8000"}})
    bus = MagicMock()
    # create=True: vor dem Fix gab es den Namen im Modul nicht. So scheitert der
    # RED-Lauf am Verhalten, nicht an einem AttributeError beim Patchen.
    with patch("routes.pipeline.get_config", return_value=cfg), \
         patch("routes.pipeline.get_log_event_bus", return_value=bus, create=True), \
         patch("routes.pipeline._find_sdd", return_value="sdd"), \
         patch("routes.pipeline._enriched_env", return_value={}), \
         patch("threading.Thread") as thread:
        yield bus, thread


def test_evaluate_meldet_sich_im_log_bus(umgebung):
    from routes.pipeline import trigger_evaluate

    bus, thread = umgebung
    ergebnis = trigger_evaluate("SPEC-0007")
    assert ergebnis["ok"] is True
    bus.mark_active.assert_called_once_with("SPEC-0007")
    kopf = [c.args[1] for c in bus.publish.call_args_list]
    assert any("sdd evaluate SPEC-0007" in z for z in kopf), kopf
    thread.assert_called_once()


def test_implement_meldet_sich_im_log_bus(umgebung):
    from routes.pipeline import trigger_implement

    bus, thread = umgebung
    trigger_implement("SPEC-0007")
    bus.mark_active.assert_called_once_with("SPEC-0007")
    kopf = [c.args[1] for c in bus.publish.call_args_list]
    assert any("sdd implement SPEC-0007" in z for z in kopf), kopf


def test_kein_verweis_auf_das_nicht_importierte_modul():
    """Die Ursache selbst: ein Modulname, der in der Datei nie importiert wird."""
    import inspect

    import routes.pipeline as pipeline

    assert "sdd_context.get_log_event_bus" not in inspect.getsource(pipeline)
