"""Integration tests für PUT /api/docs/{doc_id}/analyze — TST-0013.

Contract: CON-0013 + CON-0014 · Spec: SPEC-0005
Alle Claude Code CLI-Aufrufe werden gemockt — kein echter claude-Prozess nötig.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# ─── Path setup ──────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tool" / "sdd_cli" / "web" / "api"))
sys.path.insert(0, str(REPO_ROOT / "tool"))

os.environ.setdefault("SDD_PROJECT_ROOT", str(REPO_ROOT))

import analyzer
import sdd_context

sdd_context.init(REPO_ROOT)

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

# ─── Beispiel-Inhalt ─────────────────────────────────────────────────────────

SPEC_CONTENT = """\
---
id: SPEC-TEST
title: Test Spec
status: draft
---

## Ziele

Testfeature implementieren.

## Erfolgskriterien

- [ ] Feature ist implementiert
"""

CONTRACT_CONTENT = """\
---
id: CON-TEST
title: Test Contract
type: api
status: draft
---

## Garantien

### G-01

Der Endpoint antwortet mit HTTP 200.
"""

# ─── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def reset_sessions():
    """Leert den Session-Store vor und nach jedem Test."""
    analyzer._sessions.clear()
    yield
    analyzer._sessions.clear()


# ─── Helper ──────────────────────────────────────────────────────────────────

CLAUDE_BIN = "/usr/bin/claude"  # Dummy-Pfad; shutil.which wird gemockt


def _make_proc(
    questions: list[dict] | None = None,
    issues: list[dict] | None = None,
    suggestions: list[dict] | None = None,
    raw_stdout: str | None = None,
    returncode: int = 0,
) -> subprocess.CompletedProcess:
    """Erstellt ein CompletedProcess-Objekt wie es subprocess.run zurückgeben würde."""
    if raw_stdout is not None:
        stdout = raw_stdout
    else:
        inner = json.dumps({
            "questions": questions if questions is not None else [],
            "issues": issues if issues is not None else [],
            "suggestions": suggestions if suggestions is not None else [],
        })
        # claude --output-format json umhüllt die Antwort in einem Wrapper-Objekt
        stdout = json.dumps({
            "type": "result",
            "subtype": "success",
            "is_error": False,
            "result": inner,
            "total_cost_usd": 0.001,
        })
    return subprocess.CompletedProcess(
        args=[CLAUDE_BIN, "--print", "--output-format", "json"],
        returncode=returncode,
        stdout=stdout,
        stderr="",
    )


_CLI_WHICH = "sdd_cli.llm.providers.claude_cli.shutil.which"
_CLI_RUN   = "sdd_cli.llm.providers.claude_cli.subprocess.run"


def _patch_cli(proc: subprocess.CompletedProcess | None = None, side_effect=None):
    """Patcht shutil.which + subprocess.run im ClaudeCliCompletionProvider gemeinsam."""
    which_patch = patch(_CLI_WHICH, return_value=CLAUDE_BIN)
    run_kwargs = {"side_effect": side_effect} if side_effect else {"return_value": proc or _make_proc()}
    run_patch = patch(_CLI_RUN, **run_kwargs)
    return which_patch, run_patch


# ─── TC-01: Happy Path — Spec-Analyse ────────────────────────────────────────


def test_tc01_happy_path_spec():
    """HTTP 200, Fragen mit allen Feldern, session_id gesetzt (CON-0014 §200)."""
    questions = [
        {"id": "q1", "section": "Ziele", "text": "Was ist das Erfolgskriterium?", "severity": "warning"},
        {"id": "q2", "section": "Ziele", "text": "Welche Edge Cases gibt es?", "severity": "suggestion"},
        {"id": "q3", "section": "Erfolgskriterien", "text": "Wie wird gemessen?", "severity": "error"},
    ]
    wp, rp = _patch_cli(_make_proc(questions=questions))

    with wp, rp:
        res = client.put("/api/docs/SPEC-TEST/analyze", json={
            "content": SPEC_CONTENT,
            "doc_type": "spec",
        })

    assert res.status_code == 200
    body = res.json()
    assert body["session_id"], "session_id muss gesetzt sein"
    assert len(body["questions"]) == 3
    assert len(body["questions"]) <= 5  # INV-01
    for q in body["questions"]:
        assert {"id", "section", "text", "severity"} <= q.keys()


# ─── TC-02: Session-Tracking — beantwortete Fragen werden nicht wiederholt ───


def test_tc02_session_tracking_answered_questions_not_repeated():
    """q1 beantwortet → erscheint in zweiter Response nicht (CON-0014 INV-03)."""
    first_proc = _make_proc(questions=[
        {"id": "q1", "section": "Ziele", "text": "Frage 1?", "severity": "warning"},
        {"id": "q2", "section": "Ziele", "text": "Frage 2?", "severity": "suggestion"},
    ])
    second_proc = _make_proc(questions=[
        {"id": "q2", "section": "Ziele", "text": "Frage 2?", "severity": "suggestion"},
    ])

    wp = patch(_CLI_WHICH, return_value=CLAUDE_BIN)
    rp = patch(_CLI_RUN, side_effect=[first_proc, second_proc])

    with wp, rp:
        res1 = client.put("/api/docs/SPEC-TEST/analyze", json={
            "content": SPEC_CONTENT,
            "doc_type": "spec",
        })
        assert res1.status_code == 200
        session_id = res1.json()["session_id"]

        res2 = client.put("/api/docs/SPEC-TEST/analyze", json={
            "content": SPEC_CONTENT,
            "doc_type": "spec",
            "session_id": session_id,
            "answered_questions": [{"id": "q1", "answer": "Das Kriterium ist X."}],
        })

    assert res2.status_code == 200
    question_ids = [q["id"] for q in res2.json()["questions"]]
    assert "q1" not in question_ids, "beantwortete Frage darf nicht erneut erscheinen"


# ─── TC-03: claude nicht im PATH → HTTP 503 ──────────────────────────────────


def test_tc03_claude_not_found_returns_503():
    """shutil.which('claude') == None → HTTP 503 mit error + install_url (CON-0014 §503)."""
    with patch(_CLI_WHICH, return_value=None):
        res = client.put("/api/docs/SPEC-TEST/analyze", json={
            "content": SPEC_CONTENT,
            "doc_type": "spec",
        })

    assert res.status_code == 503
    body = res.json()["detail"]
    assert body["error"] == "provider_not_found"
    assert "install_url" in body


# ─── TC-04: Subprocess-Timeout → HTTP 504 ────────────────────────────────────


def test_tc04_timeout_returns_504():
    """subprocess.TimeoutExpired → HTTP 504 (CON-0014 §504)."""
    timeout_exc = subprocess.TimeoutExpired(cmd="claude", timeout=30)
    wp, rp = _patch_cli(side_effect=timeout_exc)

    with wp, rp:
        res = client.put("/api/docs/SPEC-TEST/analyze", json={
            "content": SPEC_CONTENT,
            "doc_type": "spec",
        })

    assert res.status_code == 504
    assert res.json()["detail"]["error"] == "provider_timeout"


# ─── TC-05: Claude gibt kein valides JSON → HTTP 502 ─────────────────────────


def test_tc05_invalid_json_returns_502():
    """Prosa-Antwort statt JSON → HTTP 502 mit raw-Feld (CON-0014 §502)."""
    wp, rp = _patch_cli(_make_proc(raw_stdout="Ich bin ein Sprachmodell und kann das nicht beantworten."))

    with wp, rp:
        res = client.put("/api/docs/SPEC-TEST/analyze", json={
            "content": SPEC_CONTENT,
            "doc_type": "spec",
        })

    assert res.status_code == 502
    body = res.json()["detail"]
    assert body["error"] == "provider_parse_error"
    assert "raw" in body


# ─── TC-06: doc_type beeinflusst Prompt ──────────────────────────────────────


def test_tc06_doc_type_influences_prompt():
    """Spec- und Contract-Prompt unterscheiden sich (CON-0013 G-04)."""
    captured: list[str] = []

    def capture_run(cmd, **kwargs):
        # Der Prompt geht über stdin (CON-0233 INV-02)
        captured.append(kwargs["input"])
        return _make_proc()

    with patch(_CLI_WHICH, return_value=CLAUDE_BIN), \
         patch(_CLI_RUN, side_effect=capture_run):
        res_spec = client.put("/api/docs/SPEC-TEST/analyze", json={
            "content": SPEC_CONTENT,
            "doc_type": "spec",
        })
        res_contract = client.put("/api/docs/CON-TEST/analyze", json={
            "content": CONTRACT_CONTENT,
            "doc_type": "contract",
        })

    assert res_spec.status_code == 200
    assert res_contract.status_code == 200
    assert len(captured) == 2
    assert "spec" in captured[0].lower()
    assert "contract" in captured[1].lower()
    assert captured[0] != captured[1]


# ─── TC-07: Maximal 5 Fragen ──────────────────────────────────────────────────


def test_tc07_max_5_questions():
    """Claude gibt 8 Fragen → Response enthält maximal 5 (CON-0014 INV-01)."""
    eight_questions = [
        {"id": f"q{i}", "section": "Ziele", "text": f"Frage {i}?", "severity": "warning"}
        for i in range(1, 9)
    ]
    wp, rp = _patch_cli(_make_proc(questions=eight_questions))

    with wp, rp:
        res = client.put("/api/docs/SPEC-TEST/analyze", json={
            "content": SPEC_CONTENT,
            "doc_type": "spec",
        })

    assert res.status_code == 200
    assert len(res.json()["questions"]) <= 5


# ─── Edge Cases ──────────────────────────────────────────────────────────────


def test_empty_content_returns_422():
    """Leerer content → HTTP 422."""
    res = client.put("/api/docs/SPEC-TEST/analyze", json={
        "content": "   ",
        "doc_type": "spec",
    })
    assert res.status_code == 422


def test_invalid_doc_type_returns_422():
    """Ungültiger doc_type → HTTP 422."""
    wp, rp = _patch_cli()
    with wp, rp:
        res = client.put("/api/docs/SPEC-TEST/analyze", json={
            "content": SPEC_CONTENT,
            "doc_type": "adr",
        })
    assert res.status_code == 422


def test_long_content_is_truncated():
    """Inhalt > 50 000 Zeichen wird auf MAX_CONTENT_CHARS gekürzt (CON-0013 INV-03)."""
    captured: list[str] = []

    def capture_run(cmd, **kwargs):
        captured.append(kwargs["input"])
        return _make_proc()

    long_content = "A" * 60_000
    with patch(_CLI_WHICH, return_value=CLAUDE_BIN), \
         patch(_CLI_RUN, side_effect=capture_run):
        res = client.put("/api/docs/SPEC-TEST/analyze", json={
            "content": long_content,
            "doc_type": "spec",
        })

    assert res.status_code == 200
    assert "A" * 60_000 not in captured[0]


def test_max_answered_questions_evicts_oldest():
    """Mehr als MAX_ANSWERED beantwortete Fragen → älteste werden verdrängt (SPEC-0005 §6 NFR)."""
    wp = patch(_CLI_WHICH, return_value=CLAUDE_BIN)
    rp = patch(_CLI_RUN, return_value=_make_proc())

    # 25 beantwortete Fragen schicken (> MAX_ANSWERED=20)
    many_answers = [{"id": f"q{i}", "answer": f"Antwort {i}"} for i in range(25)]

    with wp, rp:
        res = client.put("/api/docs/SPEC-TEST/analyze", json={
            "content": SPEC_CONTENT,
            "doc_type": "spec",
            "answered_questions": many_answers,
        })

    assert res.status_code == 200
    # Session darf maximal MAX_ANSWERED Einträge haben
    sessions = list(analyzer._sessions.values())
    assert len(sessions) == 1
    assert len(sessions[0].answered) <= analyzer.MAX_ANSWERED
    # Die neuesten Antworten bleiben erhalten (q5..q24), die ältesten (q0..q4) fallen raus
    kept_ids = {a.id for a in sessions[0].answered}
    assert "q24" in kept_ids
    assert "q0" not in kept_ids
