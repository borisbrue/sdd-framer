# AUTO-GENERATED from CON-0211 via sdd test generate — do not delete
"""TST-0240 – CON-0211: Pipeline-Monitor und Web-Routen.

Spec: SPEC-0058 · Contract: CON-0211
Die Leseschnittstelle wird mit echten Run-Verzeichnissen geprüft; Ende-zu-Ende-Fälle laufen
`sdd pipeline run` gegen den Fake-LLM-Server (tests/support/fake_llm.py).
"""
from __future__ import annotations

import asyncio
import json
import time

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from tests.support.fake_llm import FakeLLM
from tests.support.pipeline_project import (
    abnahme,
    command,
    implementierung,
    make_pipeline_project,
    review,
    rot_test,
    task,
    zerlegung,
)

T1 = task("Start", ["FR-01"], "src/start.sh")
DAG_FELDER = {"run_id", "task_id", "status", "agent", "model", "timestamp", "details"}
DAG_STATUS = {"pending", "running", "done", "failed", "skipped", "paused"}


@pytest.fixture()
def llm():
    fake = FakeLLM().start()
    yield fake
    fake.stop()


def _run(root, spec="SPEC-0900", status="running"):
    from sdd_cli.pipeline.store import RunStore

    store = RunStore.create(root, spec)
    store.write_run({"run_id": store.run_id, "spec_id": spec, "started_at": "2026-09-26T10:00:00Z",
                     "sdd_version": "0", "roles": {"implementer": {"provider": "openai-compat",
                                                                   "model": "qwen",
                                                                   "role_version": "1.0.0"}},
                     "warnings": []})
    store.write_state({"run_id": store.run_id, "status": status, "phase": "tasks",
                       "revisions": 0, "tasks": [{"task_id": "T01", "state": "red",
                                                  "attempts": 1}], "pending_request_id": None})
    return store


def _ereignisse_T01(store):
    store.event("transition", task_id="T01", to="red", detail={}, **{"from": "pending"})
    store.event("role_call", task_id="T01", role="implementer", call_id="c1", attempt=1,
                outcome="gate_failed", detail={"provider": "openai-compat", "model": "qwen"})
    store.event("transition", task_id="T01", to="done", **{"from": "reviewed"})
    store.event("warning", detail={"message": "ohne Task"})


def _app(root, monkeypatch):
    import sdd_context

    from sdd_cli.config import load_config
    from sdd_cli.web.api.routes.dag_monitor import router

    monkeypatch.setattr(sdd_context, "_root", root)
    monkeypatch.setattr(sdd_context, "_config", load_config(root))
    app = FastAPI()
    app.include_router(router, prefix="/api")
    return app


async def _get(app, pfad, **kw):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        return await c.request(kw.pop("method", "GET"), pfad, **kw)


def test_tc01_leseschnittstelle_listet_runs(tmp_path):
    """Scenario: Leseschnittstelle listet Runs (CON-0211)."""
    from sdd_cli.pipeline import monitor

    alt = _run(tmp_path, status="completed")
    time.sleep(1.1)
    neu = _run(tmp_path, status="awaiting_supervisor")
    runs = monitor.list_runs(tmp_path)
    assert [r["run_id"] for r in runs] == [neu.run_id, alt.run_id]
    assert [r["status"] for r in runs] == ["paused", "done"]
    assert all({"run_id", "spec_id", "status", "started_at"} <= set(r) for r in runs)
    assert isinstance(runs[0]["started_at"], float)


def test_tc02_ereignisse_eines_tasks_im_dagevent_format(tmp_path):
    """Scenario: Ereignisse eines Tasks im DagEvent-Format (CON-0211)."""
    from sdd_cli.pipeline import monitor

    store = _run(tmp_path)
    _ereignisse_T01(store)
    ereignisse, offset = monitor.task_events(tmp_path, store.run_id, 0)
    assert offset == 4 and len(ereignisse) == 3
    assert all(set(e) >= DAG_FELDER and e["status"] in DAG_STATUS for e in ereignisse)
    assert [e["status"] for e in ereignisse] == ["running", "running", "done"]
    rolle = ereignisse[1]
    assert (rolle["agent"], rolle["model"]) == ("local", "qwen")
    assert "implementer" in rolle["details"] and "gate_failed" in rolle["details"]


def test_tc03_offset_liefert_nur_neue_ereignisse(tmp_path):
    """Scenario: Offset liefert nur neue Ereignisse (CON-0211)."""
    from sdd_cli.pipeline import monitor

    store = _run(tmp_path)
    store.event("transition", task_id="T01", to="red", **{"from": "pending"})
    erste, offset = monitor.task_events(tmp_path, store.run_id, 0)
    store.event("transition", task_id="T01", to="halted", **{"from": "red"})
    neue, offset2 = monitor.task_events(tmp_path, store.run_id, offset)
    assert len(erste) == 1 and [e["status"] for e in neue] == ["failed"] and offset2 == 2


def _voller_lauf(tmp_path, monkeypatch, llm):
    p = make_pipeline_project(tmp_path, monkeypatch, llm, frs=("FR-01",))
    llm.antworte("decomposer", zerlegung(T1))
    llm.antworte("supervisor", command("S1", "approve"), abnahme(FR_01="erfüllt"))
    llm.antworte("test_author", rot_test(T1))
    llm.antworte("implementer", implementierung(T1))
    llm.antworte("reviewer", review())
    assert p.run("pipeline", "run", "SPEC-0900").exit_code == 0
    return p


def test_tc04_monitor_zeigt_einen_pipeline_run(tmp_path, monkeypatch, llm):
    """Scenario: Monitor zeigt einen Pipeline-Run (CON-0211)."""
    p = make_pipeline_project(tmp_path, monkeypatch, llm)
    llm.antworte("decomposer", zerlegung(T1, task("Stop", ["FR-02"], "src/stop.sh")))
    llm.antworte("supervisor", command("S1", "approve"))
    assert p.run("pipeline", "run", "SPEC-0900", "--dry-run").exit_code == 0
    antwort = asyncio.run(_get(_app(tmp_path, monkeypatch), "/api/orchestrate/runs"))
    [run] = antwort.json()
    assert (run["run_id"], run["spec_id"], run["status"]) == (p.run_dir().name, "SPEC-0900",
                                                               "done")


def test_tc05_stream_eines_abgeschlossenen_runs(tmp_path, monkeypatch, llm):
    """Scenario: Stream eines abgeschlossenen Runs (CON-0211)."""
    p = _voller_lauf(tmp_path, monkeypatch, llm)
    app = _app(tmp_path, monkeypatch)

    async def lesen():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            async with c.stream("GET", f"/api/orchestrate/stream/{p.run_dir().name}") as r:
                assert "text/event-stream" in r.headers["content-type"]
                return [json.loads(z[5:]) async for z in r.aiter_lines() if z.startswith("data:")]

    daten = asyncio.run(asyncio.wait_for(lesen(), timeout=15))
    assert daten and all(set(d) >= DAG_FELDER for d in daten)
    assert {d["task_id"] for d in daten} == {"T01"} and daten[-1]["status"] == "done"


def test_tc06_projekt_ohne_runs(tmp_path, monkeypatch):
    """Scenario: Projekt ohne Runs (CON-0211)."""
    from sdd_cli.init import init_project

    init_project(tmp_path, title="Leer")
    assert asyncio.run(_get(_app(tmp_path, monkeypatch), "/api/orchestrate/runs")).json() == []


def test_tc07_befehls_route_ist_abgeloest(tmp_path, monkeypatch):
    """Scenario: Befehls-Route ist abgelöst (CON-0211)."""
    from sdd_cli.init import init_project

    init_project(tmp_path, title="Leer")
    antwort = asyncio.run(_get(_app(tmp_path, monkeypatch), "/api/orchestrate/command/r1",
                               method="POST", json={"command_type": "pause", "task_id": "t"}))
    assert antwort.status_code == 410 and "sdd pipeline decide" in antwort.text


def test_tc08_status_als_json(tmp_path, monkeypatch, llm):
    """Scenario: Status als JSON (CON-0211)."""
    p = make_pipeline_project(tmp_path, monkeypatch, llm, frs=("FR-01",))
    p.config(llm__roles__supervisor__mode="session")
    llm.antworte("decomposer", zerlegung(T1))
    assert p.run("pipeline", "run", "SPEC-0900").exit_code == 3
    ergebnis = p.run("pipeline", "status", p.run_dir().name, "--json")
    assert ergebnis.exit_code == 0, ergebnis.output
    daten = json.loads(ergebnis.output)
    assert daten["status"] == "awaiting_supervisor" and daten["phase"] == "decompose"
    assert daten["pending_request"]["point"] == "S1" and "tasks" in daten


class _FakePopen:
    aufrufe: list = []

    def __init__(self, args, **kw):
        _FakePopen.aufrufe.append(list(args))
        self.stdout = iter(["fertig\n"])
        self.returncode = 0

    def wait(self):
        return 0


def _web_route(tmp_path, monkeypatch, pfad, config=None):
    import sdd_context

    from sdd_cli.config import load_config
    from sdd_cli.init import init_project
    from sdd_cli.web.api.routes import pipeline as routen

    init_project(tmp_path, title="Web")
    if config:
        (tmp_path / ".sdd/config.yaml").write_text(
            (tmp_path / ".sdd/config.yaml").read_text(encoding="utf-8") + config, encoding="utf-8")
    monkeypatch.setattr(sdd_context, "_root", tmp_path)
    monkeypatch.setattr(sdd_context, "_config", load_config(tmp_path))
    monkeypatch.setattr(routen.subprocess, "Popen", _FakePopen)
    _FakePopen.aufrufe = []
    app = FastAPI()
    app.include_router(routen.router, prefix="/api")
    antwort = asyncio.run(_get(app, pfad, method="POST"))
    for _ in range(40):
        if _FakePopen.aufrufe:
            break
        time.sleep(0.05)
    return antwort


def test_tc09_implement_route_startet_die_pipeline(tmp_path, monkeypatch):
    """Scenario: Implement-Route startet die Pipeline (CON-0211)."""
    antwort = _web_route(tmp_path, monkeypatch, "/api/specs/SPEC-0900/implement")
    assert {"ok", "output"} <= set(antwort.json())
    [aufruf] = _FakePopen.aufrufe
    assert aufruf[1:4] == ["pipeline", "run", "SPEC-0900"]


def test_tc10_evaluate_route_startet_die_holdout_evaluation(tmp_path, monkeypatch):
    """Scenario: Evaluate-Route startet die Holdout-Evaluation (CON-0211)."""
    antwort = _web_route(tmp_path, monkeypatch, "/api/specs/SPEC-0900/evaluate",
                         config="\nevaluator:\n  base_url: http://localhost:9000\n")
    assert antwort.json()["ok"] is True
    [aufruf] = _FakePopen.aufrufe
    assert aufruf[1:] == ["holdout", "run", "--base-url", "http://localhost:9000",
                          "--spec", "SPEC-0900"]
