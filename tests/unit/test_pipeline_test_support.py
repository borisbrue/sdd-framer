"""Selbsttest der Testhilfen für SPEC-0053 (Fake-Server und Rollenantworten)."""
from __future__ import annotations

import httpx

from tests.support.fake_llm import FakeLLM, task_id_aus
from tests.support.pipeline_project import (
    abnahme,
    command,
    implementierung,
    review,
    rot_test,
    task,
    zerlegung,
)
from tests.support.quality_project import def_errors, schema_errors


def test_antworten_entsprechen_den_contracts():
    t = task("Start", ["FR-01"], "src/start.sh")
    assert def_errors("role_outputs", "decomposer", zerlegung(t)) == []
    assert def_errors("role_outputs", "test_author", rot_test(t)) == []
    assert def_errors("role_outputs", "implementer", implementierung(t)) == []
    assert def_errors("role_outputs", "reviewer", review(False)) == []
    assert schema_errors("supervisor_command", command("S1", "approve")) == []
    assert schema_errors("supervisor_command", abnahme(FR_01="erfüllt")) == []


def test_fake_server_mit_funktion_und_reasoning():
    fake = FakeLLM().start()
    try:
        fake.antworte("supervisor", lambda a: command("S2", "halt", reason=task_id_aus(a)),
                      reasoning_tokens=5)
        antwort = httpx.post(f"{fake.base_url}/chat/completions", json={
            "model": "fake-supervisor",
            "messages": [{"role": "user", "content": '{"task_id": "t-9"}'}]}).json()
        assert '"reason": "t-9"' in antwort["choices"][0]["message"]["content"]
        assert antwort["usage"]["completion_tokens_details"]["reasoning_tokens"] == 5
        leer = httpx.post(f"{fake.base_url}/chat/completions", json={"model": "fake-x"})
        assert leer.status_code == 500
        assert len(fake.aufrufe("supervisor")) == 1
    finally:
        fake.stop()
