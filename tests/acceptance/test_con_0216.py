# AUTO-GENERATED from CON-0216 via sdd test generate — do not delete
"""TST-0245 – CON-0216: Run-Optionen, sdd-implement, Web-Adapter und Action.

Spec: SPEC-0062 · Contract: CON-0216
Rollen laufen gegen den Fake-LLM-Server. Die Web-Route startet in tc06 und tc10 einen echten
Prozess `sdd pipeline run`; Probelauf, ohne PR und Abbruch ersetzen den Prozessstart.
"""
from __future__ import annotations

import asyncio
import threading
import time
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
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

REPO = Path(__file__).resolve().parents[2]
T1 = task("Start", ["FR-01"], "src/start.sh")
SKILL_REPO = REPO / ".claude/commands/sdd-implement.md"
SKILL_BLUEPRINT = (REPO / "tool/sdd_cli/blueprint/templates/agents-md/providers/claude"
                   / "sdd-implement.md")
ACTION_REPO = REPO / ".sdd/templates/github-actions/sdd-orchestrate.yml"
ACTION_BLUEPRINT = REPO / "tool/sdd_cli/blueprint/templates/github-actions/sdd-orchestrate.yml"


@pytest.fixture()
def llm():
    fake = FakeLLM().start()
    yield fake
    fake.stop()


@pytest.fixture()
def projekt(tmp_path, monkeypatch, llm):
    p = make_pipeline_project(tmp_path, monkeypatch, llm, frs=("FR-01",))
    p.config(evaluator__base_url="")
    return p


def _voll(llm, supervisor_s3=True):
    llm.antworte("decomposer", zerlegung(T1))
    antworten = [command("S1", "approve")] + ([abnahme(FR_01="erfüllt")] if supervisor_s3 else [])
    llm.antworte("supervisor", *antworten)
    llm.antworte("test_author", rot_test(T1))
    llm.antworte("implementer", implementierung(T1))
    llm.antworte("reviewer", review())


# ── Run-Optionen ─────────────────────────────────────────────────────────────

def test_tc01_session_rollen_pro_run(projekt, llm):
    """Scenario: Session-Rollen pro Run (CON-0216)."""
    config_vorher = (projekt.root / ".sdd/config.yaml").read_bytes()
    llm.antworte("decomposer", zerlegung(T1))
    llm.antworte("supervisor", command("S1", "approve"))
    llm.antworte("test_author", rot_test(T1))
    ergebnis = projekt.run("pipeline", "run", "SPEC-0900", "--session", "implementer")
    assert ergebnis.exit_code == 3, ergebnis.output
    run = projekt.json("run.json")
    assert run["options"]["session"] == ["implementer"]
    assert run["roles"]["implementer"]["mode"] == "session"
    assert projekt.json("pending-work.json")["role"] == "implementer"
    assert llm.aufrufe("implementer") == []
    assert (projekt.root / ".sdd/config.yaml").read_bytes() == config_vorher


def test_tc02_unbekannte_session_rolle(projekt):
    """Scenario: Unbekannte Session-Rolle (CON-0216)."""
    ergebnis = projekt.run("pipeline", "run", "SPEC-0900", "--session", "tester")
    assert ergebnis.exit_code == 2
    ausgabe = " ".join(ergebnis.output.split())
    assert "tester" in ausgabe and "implementer" in ausgabe
    assert not (projekt.root / ".sdd/runs").exists()


def test_tc03_schritte_pro_run(projekt, llm, monkeypatch):
    """Scenario: Schritte pro Run (CON-0216)."""
    from sdd_cli.pipeline import steps

    aufrufe: list[str] = []
    monkeypatch.setattr(steps, "run_finalize", lambda *a: aufrufe.append("finalize") or "pr")
    monkeypatch.setattr(steps, "automerge", lambda *a: aufrufe.append("automerge") or ("open", ""))
    _voll(llm)
    ergebnis = projekt.run("pipeline", "run", "SPEC-0900", "--auto", "--steps", "holdout")
    assert ergebnis.exit_code == 0, ergebnis.output
    assert projekt.json("run.json")["options"]["steps"] == ["holdout"]
    assert aufrufe == []
    assert projekt.json("state.json")["status"] == "completed"


@pytest.mark.parametrize("args", [["--steps", "holdout"], ["--auto", "--steps", "deploy"]])
def test_tc04_ungueltige_schrittangabe(projekt, args):
    """Scenario Outline: Ungültige Schrittangabe (CON-0216)."""
    ergebnis = projekt.run("pipeline", "run", "SPEC-0900", *args)
    assert ergebnis.exit_code == 2, ergebnis.output


# ── Skill ────────────────────────────────────────────────────────────────────

def test_tc05_skill_sdd_implement_nutzt_die_pipeline():
    """Scenario: Skill sdd-implement nutzt die Pipeline (CON-0216)."""
    text = SKILL_BLUEPRINT.read_text(encoding="utf-8")
    # Die Repo-Kopie trägt zusätzlich das scope-Frontmatter aller Repo-Skills (TST-0196).
    repo = SKILL_REPO.read_text(encoding="utf-8")
    assert repo.startswith("---\nscope: ") and repo.split("---\n", 2)[2] == text
    assert ("sdd pipeline run $ARGUMENTS --auto --session test_author --session implementer "
            "--session supervisor") in text
    assert "sdd pipeline done" in text and "sdd pipeline decide" in text
    for verboten in ("task-route", "task-exec", "sdd decompose", "sdd finalize"):
        assert verboten not in text, verboten
    assert ".sdd/holdout/` wird NIEMALS gelesen" in text


# ── Web-Adapter ──────────────────────────────────────────────────────────────

@pytest.fixture()
def web(projekt, monkeypatch):
    import sdd_context

    from sdd_cli.config import load_config
    from sdd_cli.web.api.routes import orchestrate as orch

    monkeypatch.setattr(sdd_context, "_root", projekt.root)
    monkeypatch.setattr(sdd_context, "_config", load_config(projekt.root))
    monkeypatch.setattr("sdd_cli.llm.claude_available", lambda: True)
    orch._runs.clear()
    orch._active.clear()
    app = FastAPI()
    app.include_router(orch.router, prefix="/api")
    yield TestClient(app), orch
    orch._runs.clear()
    orch._active.clear()


class _Prozess:
    """Ersatz für den Prozess `sdd pipeline run`: liefert Zeilen und einen Exit-Code."""

    def __init__(self, argv, zeilen=("ok",), code=0, blockieren=False):
        self.argv = argv
        self._zeilen = list(zeilen)
        self._code = code
        self._frei = threading.Event()
        if not blockieren:
            self._frei.set()
        self.beendet = False

    @property
    def stdout(self):
        for z in self._zeilen:
            yield z + "\n"
        self._frei.wait(10)

    def terminate(self):
        self.beendet = True
        self._code = -15
        self._frei.set()

    def wait(self):
        return self._code


def _starten(web, monkeypatch, **body):
    client, orch = web
    gestartet: list[_Prozess] = []

    def popen(argv, **kw):
        gestartet.append(_Prozess(argv))
        return gestartet[-1]

    monkeypatch.setattr(orch, "_popen", popen)
    antwort = client.post("/api/orchestrate", json={"spec_id": "SPEC-0900", **body})
    assert antwort.status_code == 202, antwort.text
    return antwort.json()["run_id"], gestartet[0].argv


def test_tc06_web_ui_startet_einen_pipeline_run(web, projekt, llm):
    """Scenario: Web-UI startet einen Pipeline-Run (CON-0216)."""
    client, _ = web
    _voll(llm)
    antwort = client.post("/api/orchestrate", json={"spec_id": "SPEC-0900"})
    assert antwort.status_code == 202, antwort.text
    run_id = antwort.json()["run_id"]
    assert (projekt.root / ".sdd/runs/SPEC-0900" / run_id / "state.json").is_file()
    zustand = client.get(f"/api/pipeline/{run_id}").json()
    assert {"run_id", "spec_id", "status", "attempts", "max_attempts", "log", "report"} <= set(
        zustand)
    assert zustand["run_id"] == run_id and zustand["status"] == "labeled", zustand["log"]
    assert any("sdd pipeline run SPEC-0900 --auto" in z for z in zustand["log"])
    assert projekt.json("run.json")["options"]["auto"] is True


def test_tc07_web_ui_ohne_pr(web, monkeypatch):
    """Scenario: Web-UI ohne PR (CON-0216)."""
    client, _ = web
    run_id, argv = _starten(web, monkeypatch, no_pr=True)
    assert argv[-6:] == ["SPEC-0900", "--auto", "--run-id", run_id, "--steps", "holdout"]
    assert client.get(f"/api/pipeline/{run_id}").json()["report"]["pr_url"] is None


def test_tc08_web_ui_im_probelauf(web, monkeypatch):
    """Scenario: Web-UI im Probelauf (CON-0216)."""
    client, _ = web
    run_id, argv = _starten(web, monkeypatch, dry_run=True)
    assert "--dry-run" in argv and "--auto" in argv
    assert client.get(f"/api/pipeline/{run_id}").json()["status"] == "dry_run"


def test_tc09_web_ui_bricht_ab(web, monkeypatch):
    """Scenario: Web-UI bricht ab (CON-0216)."""
    client, orch = web
    prozess: list[_Prozess] = []

    def popen(argv, **kw):
        prozess.append(_Prozess(argv, blockieren=True))
        return prozess[-1]

    monkeypatch.setattr(orch, "_popen", popen)
    from sdd_cli.pipeline.store import new_run_id

    run_id = new_run_id("SPEC-0900")
    orch._runs[run_id] = orch.RunState(run_id=run_id, spec_id="SPEC-0900")
    orch._active["SPEC-0900"] = run_id
    worker = threading.Thread(target=orch._run_pipeline_bg,
                              args=(run_id, orch.OrchestrateRequest(spec_id="SPEC-0900")))
    worker.start()
    ende = time.monotonic() + 10
    while not prozess and time.monotonic() < ende:
        time.sleep(0.05)
    antwort = client.post(f"/api/pipeline/{run_id}/abort")
    worker.join(10)
    assert antwort.status_code == 200 and antwort.json()["aborted"] is True
    assert prozess[0].beendet
    assert client.get(f"/api/pipeline/{run_id}").json()["status"] == "aborted"


def test_tc10_web_ui_wartet_auf_claude(web, projekt, llm):
    """Scenario: Web-UI wartet auf Claude (CON-0216)."""
    client, _ = web
    projekt.config(llm__roles__supervisor__mode="session")
    llm.antworte("decomposer", zerlegung(T1))
    run_id = client.post("/api/orchestrate", json={"spec_id": "SPEC-0900"}).json()["run_id"]
    zustand = client.get(f"/api/pipeline/{run_id}").json()
    assert zustand["status"] == "paused", zustand["log"]
    assert any(f"sdd pipeline decide {run_id}" in z for z in zustand["log"])


def test_tc11_remote_befehl_orchestrate(projekt, monkeypatch):
    """Scenario: Remote-Befehl orchestrate (CON-0216)."""
    import sdd_context

    from sdd_cli.config import load_config
    from sdd_cli.web.api.routes import chat, remote

    projekt.config(pwa={"auth": {"token": "t0k"}})
    monkeypatch.setattr(sdd_context, "_root", projekt.root)
    monkeypatch.setattr(sdd_context, "_config", load_config(projekt.root))
    aufgerufen: list[tuple] = []

    class _Stream:
        def __aiter__(self):
            return self

        async def __anext__(self):
            raise StopAsyncIteration

    class _Proc:
        stdout = _Stream()
        stderr = _Stream()

        async def wait(self):
            return 0

    async def exec_(*argv, **kw):
        aufgerufen.append(argv)
        return _Proc()

    monkeypatch.setattr(remote, "_exec", exec_)
    app = FastAPI()
    app.include_router(remote.router, prefix="/api")

    async def senden():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post("/api/sdd/run", json={"cmd": "orchestrate", "args": ["SPEC-0900"]},
                             headers={"Authorization": "Bearer t0k"})
            return r.status_code, r.text

    status, _ = asyncio.run(senden())
    assert status == 200
    assert aufgerufen == [("sdd", "pipeline", "run", "SPEC-0900", "--auto")]
    intent = chat._intent_parser.handle("orchestrate SPEC-0900")
    assert remote.sdd_argv(intent.cmd, intent.args) == ["pipeline", "run", "SPEC-0900", "--auto"]


# ── sdd start --auto und Action ──────────────────────────────────────────────

def test_tc12_sdd_start_auto(projekt, llm):
    """Scenario: sdd start --auto (CON-0216)."""
    projekt.config(llm__roles__supervisor__mode="session")
    llm.antworte("decomposer", zerlegung(T1))
    ergebnis = projekt.run("start", "SPEC-0900", "--auto", "--no-container")
    assert ergebnis.exit_code == 3, ergebnis.output
    run = projekt.json("run.json")
    assert run["spec_id"] == "SPEC-0900" and run["options"]["auto"] is True
    spec = (projekt.root / ".sdd/specs/SPEC-0900-testspec.md").read_text(encoding="utf-8")
    assert "status: approved" in spec


def test_tc13_github_action_vorlage():
    """Scenario: GitHub-Action-Vorlage (CON-0216)."""
    text = ACTION_BLUEPRINT.read_text(encoding="utf-8")
    assert ACTION_REPO.read_text(encoding="utf-8") == text
    assert "sdd pipeline run" in text and "--auto" in text
    assert "sdd orchestrate" not in text
    assert "secrets.ANTHROPIC_API_KEY" not in text
