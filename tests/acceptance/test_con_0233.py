# AUTO-GENERATED from CON-0233 via sdd test generate — do not delete
"""Contract-Tests für Aufrufform des claude-cli-Providers (CON-0233).

Spec: SPEC-0067, SPEC-0068 · Contract: CON-0233
Der echte Provider startet einen echten Prozess. An Stelle von `claude` liegt ein Skript im
`PATH`, das Argumente, Umgebung und stdin protokolliert. Kein Patch von `subprocess.run`: Nur so
fällt eine Übergabe über argv bei großen Prompts wirklich mit `E2BIG` auf.
"""
from __future__ import annotations

import json
import os
import sys

import pytest

from sdd_cli.llm.providers.claude_cli import ClaudeCliCompletionProvider

FAKE_CLAUDE = """#!{python}
import json, os, stat, sys, time

daten = sys.stdin.buffer.read().decode("utf-8")
aufruf = {{"argv": sys.argv[1:], "stdin": daten, "env": dict(os.environ), "pid": os.getpid()}}
if "--system-prompt-file" in sys.argv:
    datei = sys.argv[sys.argv.index("--system-prompt-file") + 1]
    aufruf["system_file"] = datei
    aufruf["system"] = open(datei, "rb").read().decode("utf-8")
    aufruf["system_mode"] = stat.S_IMODE(os.stat(datei).st_mode)
with open(os.environ["FAKE_LOG"], "w", encoding="utf-8") as f:
    json.dump(aufruf, f)
modus = os.environ.get("FAKE_MODE", "ok")
if modus == "sleep":
    time.sleep(30)
if modus == "ok":
    print(json.dumps({{"type": "result", "result": "antwort"}}))
elif modus == "echo":
    sys.stdout.buffer.write(json.dumps({{"type": "result", "result": daten}},
                                       ensure_ascii=False).encode("utf-8"))
elif modus == "fail_with_envelope":
    print(json.dumps({{"type": "result", "is_error": True, "result": "Fehlertext"}}))
elif modus == "fail_json_without_result":
    print(json.dumps({{"type": "result", "is_error": True}}))
sys.stderr.buffer.write(os.environ.get("FAKE_STDERR", "").encode("utf-8"))
sys.exit(int(os.environ.get("FAKE_EXIT", "0")))
"""

FLAGS = ["--print", "--output-format", "json", "--tools", "", "--setting-sources", "",
         "--strict-mcp-config", "--system-prompt-file"]


@pytest.fixture
def protokoll(tmp_path, monkeypatch):
    """Fake-`claude` vorn im PATH; liefert eine Funktion, die das Protokoll liest."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    skript = bin_dir / "claude"
    skript.write_text(FAKE_CLAUDE.format(python=sys.executable), encoding="utf-8")
    skript.chmod(0o755)
    log = tmp_path / "aufruf.json"
    monkeypatch.setenv("PATH", f"{bin_dir}:/usr/bin:/bin")
    monkeypatch.setenv("FAKE_LOG", str(log))
    monkeypatch.delenv("CLAUDE_CODE_DISABLE_AUTO_MEMORY", raising=False)
    return lambda: json.loads(log.read_text(encoding="utf-8"))


def test_tc01_agent_faehigkeiten_sind_abgeschaltet(protokoll, monkeypatch):
    """Scenario: Agent-Fähigkeiten sind abgeschaltet (CON-0233 INV-01, INV-03)."""
    monkeypatch.setenv("SDD_TESTVARIABLE", "bleibt")
    ergebnis = ClaudeCliCompletionProvider().complete("Hallo")

    aufruf = protokoll()
    assert ergebnis.text == "antwort"
    assert aufruf["argv"] == [*FLAGS, aufruf["system_file"]]
    assert aufruf["env"]["CLAUDE_CODE_DISABLE_AUTO_MEMORY"] == "1"
    assert aufruf["env"]["SDD_TESTVARIABLE"] == "bleibt"


def test_tc02_system_prompt_als_echter_system_prompt(protokoll):
    """Scenario: System-Prompt als echter System-Prompt (CON-0233 INV-01, INV-02)."""
    ClaudeCliCompletionProvider().complete("Hallo", system_prompt="Sei knapp.")

    aufruf = protokoll()
    assert aufruf["system"] == "Sei knapp."
    assert aufruf["system_mode"] == 0o600
    assert aufruf["stdin"] == "Hallo"
    assert not os.path.exists(aufruf["system_file"])


def test_tc03_ohne_system_prompt(protokoll):
    """Scenario: Ohne System-Prompt (CON-0233 INV-01, INV-02)."""
    ClaudeCliCompletionProvider().complete("Hallo")

    aufruf = protokoll()
    assert aufruf["system"] == ""
    assert aufruf["stdin"] == "Hallo"


def test_tc04_grosser_prompt(protokoll):
    """Scenario: Großer Prompt (CON-0233 INV-01, INV-02) – über der argv-Grenze von 128 KiB."""
    prompt = "x" * 200_000
    ClaudeCliCompletionProvider().complete(prompt)

    aufruf = protokoll()
    assert aufruf["stdin"] == prompt
    assert not any(prompt in arg for arg in aufruf["argv"])


def test_grosser_system_prompt(protokoll):
    """Scenario: Großer System-Prompt (CON-0233 INV-01, SPEC-0068 FR-05)."""
    system = "s" * 200_000
    ClaudeCliCompletionProvider().complete("Hallo", system_prompt=system)

    aufruf = protokoll()
    assert aufruf["system"] == system
    assert not any(system in arg for arg in aufruf["argv"])


def test_datei_wird_auch_nach_timeout_geloescht(protokoll, monkeypatch):
    """Scenario: Datei wird auch nach Timeout gelöscht (CON-0233 INV-01, INV-05)."""
    monkeypatch.setenv("FAKE_MODE", "sleep")

    with pytest.raises(RuntimeError, match="Timeout nach 1s"):
        ClaudeCliCompletionProvider().complete("Hallo", system_prompt="x", timeout=1)
    aufruf = protokoll()
    assert not os.path.exists(aufruf["system_file"])
    with pytest.raises(ProcessLookupError):
        os.kill(aufruf["pid"], 0)


def test_tc05_cli_scheitert_ohne_envelope(protokoll, monkeypatch):
    """Scenario: CLI scheitert ohne Envelope (CON-0233 INV-04)."""
    monkeypatch.setenv("FAKE_MODE", "fail_no_envelope")
    monkeypatch.setenv("FAKE_EXIT", "2")
    monkeypatch.setenv("FAKE_STDERR", "error: unknown option '--tools'")

    with pytest.raises(RuntimeError) as exc:
        ClaudeCliCompletionProvider().complete("Hallo")
    assert "Exit-Code 2" in str(exc.value)
    assert "unknown option" in str(exc.value)
    assert not os.path.exists(protokoll()["system_file"])


def test_tc06_umlaute_und_sonderzeichen(protokoll, monkeypatch):
    """Scenario: Umlaute und Sonderzeichen unter C-Locale (CON-0233 INV-02)."""
    monkeypatch.setenv("LC_ALL", "C")
    monkeypatch.setenv("LANG", "C")
    monkeypatch.setenv("FAKE_MODE", "echo")
    ergebnis = ClaudeCliCompletionProvider().complete("Grüße – ✓", system_prompt="Läuft ✓")

    aufruf = protokoll()
    assert aufruf["stdin"] == "Grüße – ✓" and aufruf["system"] == "Läuft ✓"
    assert ergebnis.text == "Grüße – ✓"


def test_fehlermeldung_mit_umlauten_unter_c_locale(protokoll, monkeypatch):
    """Scenario: Fehlermeldung mit Umlauten unter C-Locale (CON-0233 INV-02, INV-04)."""
    monkeypatch.setenv("LC_ALL", "C")
    monkeypatch.setenv("LANG", "C")
    monkeypatch.setenv("FAKE_MODE", "fail_no_envelope")
    monkeypatch.setenv("FAKE_EXIT", "2")
    monkeypatch.setenv("FAKE_STDERR", "Fehlä ✓")

    with pytest.raises(RuntimeError) as exc:
        ClaudeCliCompletionProvider().complete("Hallo")
    assert "Exit-Code 2" in str(exc.value) and "Fehlä ✓" in str(exc.value)


def test_tc07_lange_fehlermeldung_wird_gekuerzt(protokoll, monkeypatch):
    """Scenario: Lange Fehlermeldung wird gekürzt (CON-0233 INV-04)."""
    monkeypatch.setenv("FAKE_MODE", "fail_no_envelope")
    monkeypatch.setenv("FAKE_EXIT", "3")
    monkeypatch.setenv("FAKE_STDERR", "#" * 1000 + "B" * 500)

    with pytest.raises(RuntimeError) as exc:
        ClaudeCliCompletionProvider().complete("Hallo")
    meldung = str(exc.value)
    assert "Exit-Code 3" in meldung and "B" * 500 in meldung
    assert "#" not in meldung


def test_tc08_cli_scheitert_mit_json_ohne_result(protokoll, monkeypatch):
    """Scenario: CLI scheitert mit JSON ohne result (CON-0233 INV-04)."""
    monkeypatch.setenv("FAKE_MODE", "fail_json_without_result")
    monkeypatch.setenv("FAKE_EXIT", "1")

    with pytest.raises(RuntimeError, match="Exit-Code 1"):
        ClaudeCliCompletionProvider().complete("Hallo")


def test_tc09_cli_scheitert_mit_envelope(protokoll, monkeypatch):
    """Scenario: CLI scheitert mit Envelope (CON-0233 INV-04)."""
    monkeypatch.setenv("FAKE_MODE", "fail_with_envelope")
    monkeypatch.setenv("FAKE_EXIT", "1")

    assert ClaudeCliCompletionProvider().complete("Hallo").text == "Fehlertext"
