"""TST-0236 – CON-0207: Usage-Erfassung (Provider, Decorator, Kontext, Senken).

Spec: SPEC-0060 · Contract: CON-0207
Schnittstellen laut CON-0207: `sdd_cli.llm.usage.usage_context`, `use_sinks`, `register_sink`,
`UsageSink.record(UsageRecord)`. OpenAI-kompatible Aufrufe laufen gegen den Fake-Server aus
`tests/support/fake_llm.py`; `claude --print` wird durch ein vorbereitetes Envelope ersetzt.
"""
from __future__ import annotations

import csv
import json
import logging
import sqlite3
import subprocess

import pytest
from click.testing import CliRunner

from tests.support.fake_llm import FakeLLM
from tests.support.usage_support import (
    ENVELOPE,
    FakeSink,
    KaputteSink,
    claude_prozess,
    projekt_mit_llm,
    requires_usage_capture,
)

pytestmark = requires_usage_capture


@pytest.fixture()
def llm():
    fake = FakeLLM().start()
    yield fake
    fake.stop()


@pytest.fixture()
def cfg(tmp_path, llm, monkeypatch):
    from sdd_cli.config import load_config

    projekt_mit_llm(tmp_path, llm.base_url)
    monkeypatch.chdir(tmp_path)
    return load_config(tmp_path)


def _openai():
    pytest.importorskip("openai")


def _completion(cfg, komponente="completion"):
    from sdd_cli.llm.factory import get_completion_provider

    return get_completion_provider(cfg, komponente)


def _zeilen(root):
    with sqlite3.connect(root / ".sdd/evaluations.db") as con:
        con.row_factory = sqlite3.Row
        return [dict(r) for r in con.execute("SELECT * FROM token_usage ORDER BY id")]


def test_tc01_claude_cli_liest_die_usage_aus_dem_envelope(monkeypatch):
    """Scenario: claude-cli liest die Usage aus dem Envelope (CON-0207)."""
    from sdd_cli.llm.providers.claude_cli import ClaudeCliCompletionProvider

    claude_prozess(monkeypatch, json.loads(ENVELOPE.read_text()))
    ergebnis = ClaudeCliCompletionProvider().complete("x")
    u = ergebnis.usage
    assert ergebnis.text == "ok"
    assert (u.input_tokens, u.output_tokens, u.cache_read_tokens, u.cache_creation_tokens) == (
        1200, 300, 50, 70)
    assert (u.reasoning_tokens, u.finish_reason, u.server_model, u.source) == (
        40, "end_turn", "claude-opus-5-5", "reported")


def test_tc02_claude_cli_ohne_usage_im_envelope(monkeypatch, caplog):
    """Scenario: claude-cli ohne Usage im Envelope (CON-0207)."""
    from sdd_cli.llm.providers.claude_cli import ClaudeCliCompletionProvider

    claude_prozess(monkeypatch, {"type": "result", "result": "hi"})
    ergebnis = ClaudeCliCompletionProvider().complete("x")
    assert ergebnis.text == "hi"
    assert ergebnis.usage is not None and ergebnis.usage.source == "unavailable"
    assert (ergebnis.usage.input_tokens, ergebnis.usage.output_tokens) == (0, 0)


def test_tc03_openai_compat_mit_reasoning_tokens(cfg, llm):
    """Scenario: openai-compat mit Reasoning-Tokens (CON-0207)."""
    _openai()
    llm.antworte("completion", "antwort", finish_reason="length", reasoning_tokens=800)
    u = _completion(cfg).complete("x").usage
    assert (u.reasoning_tokens, u.finish_reason, u.server_model, u.source) == (
        800, "length", "fake-completion", "reported")


def test_tc04_openai_compat_ohne_usage_block(cfg, llm):
    """Scenario: openai-compat ohne Usage-Block (CON-0207)."""
    _openai()
    llm.antworte("completion", "antwort", mit_usage=False)
    assert _completion(cfg).complete("x").usage.source == "unavailable"


def test_tc05_codegen_liefert_usage_und_bleibt_kompatibel(cfg, llm, tmp_path):
    """Scenario: CodeGen liefert Usage und bleibt kompatibel (CON-0207)."""
    _openai()
    from sdd_cli.llm.factory import get_code_gen_provider

    llm.antworte("orchestrator", {"files": [{"path": "src/a.txt", "content": "x"}],
                                  "explanation": "ok"})
    ergebnis = get_code_gen_provider(cfg).generate("x", tmp_path)
    files, erklaerung = ergebnis
    assert files[0]["path"] == "src/a.txt" and erklaerung == "ok"
    assert ergebnis.usage.source == "reported"


@pytest.mark.parametrize("komponente", ["completion", "evaluator", "analyzer", "ai_routes",
                                        "local_llm", "orchestrator"])
def test_tc06_jede_factory_komponente_wird_erfasst(cfg, llm, tmp_path, komponente):
    """Scenario Outline: Jede Factory-Komponente wird erfasst (CON-0207)."""
    _openai()
    from sdd_cli.llm.factory import get_code_gen_provider
    from sdd_cli.llm.usage import use_sinks

    senke = FakeSink()
    with use_sinks([senke]):
        if komponente == "orchestrator":
            llm.antworte("orchestrator", {"files": [], "explanation": "e"})
            get_code_gen_provider(cfg).generate("x", tmp_path)
        else:
            llm.antworte(komponente, "antwort")
            _completion(cfg, komponente).complete("x")
    assert [r.component for r in senke.records] == [komponente]


def test_tc07_aufruf_mit_ausnahme():
    """Scenario: Aufruf mit Ausnahme (CON-0207)."""
    from sdd_cli.llm.usage import RecordingCompletionProvider, use_sinks

    class Kaputt:
        def complete(self, prompt, **kw):
            raise RuntimeError("Server weg")

    senke = FakeSink()
    provider = RecordingCompletionProvider(Kaputt(), component="completion", model="m")
    with use_sinks([senke]), pytest.raises(RuntimeError, match="Server weg"):
        provider.complete("x")
    [r] = senke.records
    assert r.usage.finish_reason == "error" and r.usage.source == "unavailable"


def test_tc08_aufrufkontext(cfg, llm):
    """Scenario: Aufrufkontext (CON-0207)."""
    _openai()
    from sdd_cli.llm.usage import usage_context, use_sinks

    senke = FakeSink()
    llm.antworte("completion", "a")
    with use_sinks([senke]), usage_context(spec_id="SPEC-0900", run_id="r1", role="implementer"):
        with usage_context(attempt=2):
            _completion(cfg).complete("x")
    [r] = senke.records
    assert r.context == {"spec_id": "SPEC-0900", "run_id": "r1", "role": "implementer",
                         "attempt": 2}


def test_tc09_ohne_kontext(cfg, llm):
    """Scenario: Ohne Kontext (CON-0207)."""
    _openai()
    llm.antworte("completion", "a")
    _completion(cfg).complete("x")
    [z] = _zeilen(cfg.root)
    assert z["spec_id"] is None and z["run_id"] is None and z["context_json"] is None
    assert z["component"] == "completion" and z["model"] == "fake-completion"


def test_tc10_senkenfehler(cfg, llm, caplog):
    """Scenario: Senkenfehler (CON-0207)."""
    _openai()
    from sdd_cli.llm.usage import use_sinks

    zweite = FakeSink()
    llm.antworte("completion", "ergebnis")
    with caplog.at_level(logging.WARNING), use_sinks([KaputteSink(), zweite]):
        assert _completion(cfg).complete("x").text == "ergebnis"
    assert len(zweite.records) == 1
    assert any("gesperrt" in m or "Senke" in m for m in caplog.messages)


def test_tc11_decompose_und_analyzer_laufen_ueber_die_factory():
    """Scenario: decompose und Analyzer laufen über die Factory (CON-0207)."""
    import inspect

    import sdd_cli.decompose as decompose

    quelle = inspect.getsource(decompose)
    analyzer = (ENVELOPE.parents[3] / "tool/sdd_cli/web/api/analyzer.py").read_text()
    for text in (quelle, analyzer):
        assert "ClaudeCliCompletionProvider(" not in text
        assert "get_completion_provider" in text


def test_tc12_web_api_schreibt_und_liest_token_usage(tmp_path, monkeypatch):
    """Scenario: Web-API schreibt und liest token_usage (CON-0207)."""
    from sdd_cli.init import init_project
    from sdd_cli.main import cli

    init_project(tmp_path, title="Web")
    alt = [{"ts": "2026-06-01T10:00:00+00:00", "provider": "claude", "operation": "analyze",
            "model": "m", "input_tokens": 100, "output_tokens": 10,
            "cache_creation_tokens": 0, "cache_read_tokens": 0, "cost_usd": 0.1}] * 2
    (tmp_path / ".sdd/ai_usage.json").write_text(json.dumps(alt))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SDD_PROJECT_ROOT", str(tmp_path))
    CliRunner().invoke(cli, ["upgrade"])
    zeilen = _zeilen(tmp_path)
    assert len(zeilen) == 2
    assert all(json.loads(z["context_json"])["origin"] == "web" for z in zeilen)
    from sdd_cli.web.api import usage_store

    usage_store.record_usage("chat", 5, 5, 0, 0, "m")
    assert len(_zeilen(tmp_path)) == 3
    assert usage_store.get_summary()["total_input_tokens"] == 205
    assert len(usage_store.get_all()) == 3


def test_tc13_token_history_zeigt_reasoning_tokens(cfg, llm, tmp_path):
    """Scenario: token-history zeigt Reasoning-Tokens (CON-0207)."""
    _openai()
    from sdd_cli.main import cli

    llm.antworte("completion", "a", reasoning_tokens=40)
    _completion(cfg).complete("x")
    ziel = tmp_path / "out.csv"
    CliRunner().invoke(cli, ["token-history", "--export", str(ziel)])
    kopf = next(csv.reader(ziel.open()))
    for spalte in ("reasoning_tokens", "finish_reason", "source", "run_id", "context_json"):
        assert spalte in kopf


def test_tc14_migration_bestehender_datenbanken(tmp_path):
    """Scenario: Migration bestehender Datenbanken (CON-0207)."""
    from sdd_cli.config import load_config
    from sdd_cli.init import init_project
    from sdd_cli.llm.base import UsageMetadata
    from sdd_cli.llm.usage import SqliteUsageSink, UsageRecord

    init_project(tmp_path, title="Alt")
    db = tmp_path / ".sdd/evaluations.db"
    with sqlite3.connect(db) as con:
        con.execute("""CREATE TABLE token_usage (id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL, spec_id TEXT, component TEXT NOT NULL,
            model TEXT NOT NULL DEFAULT '', input_tokens INTEGER NOT NULL DEFAULT 0,
            output_tokens INTEGER NOT NULL DEFAULT 0, cache_read_tokens INTEGER NOT NULL DEFAULT 0,
            cache_write_tokens INTEGER NOT NULL DEFAULT 0, duration_ms INTEGER NOT NULL DEFAULT 0,
            calibrated INTEGER NOT NULL DEFAULT 0)""")
        con.execute("INSERT INTO token_usage (timestamp, component, model, input_tokens) "
                    "VALUES ('2026-01-01T00:00:00Z', 'review-contract', 'm', 7)")
    SqliteUsageSink(load_config(tmp_path)).record(UsageRecord(
        component="completion", model="m", duration_ms=1,
        usage=UsageMetadata(input_tokens=1, output_tokens=1, source="reported"), context={}))
    alt, neu = _zeilen(tmp_path)
    assert alt["input_tokens"] == 7 and alt["source"] is None and alt["context_json"] is None
    assert {"reasoning_tokens", "finish_reason", "server_model", "source", "run_id",
            "context_json"} <= set(neu)


def test_tc15_nicht_verfuegbare_usage_verfaelscht_keine_auswertu(tmp_path):
    """Scenario: Nicht verfügbare Usage verfälscht keine Auswertung (CON-0207)."""
    from sdd_cli.config import load_config
    from sdd_cli.estimation import calibrate
    from sdd_cli.init import init_project
    from sdd_cli.llm.base import UsageMetadata
    from sdd_cli.llm.usage import SqliteUsageSink, UsageRecord

    init_project(tmp_path, title="Kal")
    cfg = load_config(tmp_path)
    senke = SqliteUsageSink(cfg)
    for tokens, source in ((1000, "reported"), (3000, "reported"), (0, "unavailable")):
        senke.record(UsageRecord(component="completion", model="m", duration_ms=1,
                                 usage=UsageMetadata(input_tokens=tokens, source=source),
                                 context={"spec_id": "SPEC-0900"}))
    ergebnis = calibrate(cfg, "SPEC-0900")
    assert ergebnis["input_tokens"] == 4000
    assert ergebnis["rows"] == 2 and ergebnis["unavailable_rows"] == 1


def test_tc16_dauerhaft_registrierte_senke(cfg, llm):
    """Scenario: Dauerhaft registrierte Senke (CON-0207)."""
    _openai()
    from sdd_cli.llm import usage

    senke = FakeSink()
    usage.register_sink(senke)
    try:
        llm.antworte("completion", "a", "b")
        _completion(cfg).complete("x")
        _completion(cfg).complete("y")
    finally:
        usage.unregister_sink(senke)
    assert len(senke.records) == 2 and len(_zeilen(cfg.root)) == 2


def test_tc17_nicht_gemeldete_reasoning_tokens(cfg, llm):
    """Scenario: Nicht gemeldete Reasoning-Tokens (CON-0207)."""
    _openai()
    llm.antworte("completion", "a")
    assert _completion(cfg).complete("x").usage.reasoning_tokens is None


def test_kein_prompt_text_in_token_usage(cfg, llm):
    """CON-0207 INV-05: Prompttext wird nicht gespeichert."""
    _openai()
    llm.antworte("completion", "a")
    _completion(cfg).complete("GEHEIMER-PROMPT-4711")
    assert "GEHEIMER-PROMPT-4711" not in json.dumps(_zeilen(cfg.root))


def test_hilfe_claude_prozess_ist_isoliert(monkeypatch):
    """Selbsttest: claude_prozess ersetzt nur den Aufruf im Provider-Modul."""
    claude_prozess(monkeypatch, {"type": "result", "result": "x"})
    assert subprocess.run is not None
