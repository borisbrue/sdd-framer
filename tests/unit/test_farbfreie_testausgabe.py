"""Die Testsuite hängt nicht davon ab, ob die Shell Farbe erzwingt (#124).

Die rich-Console in `sdd_cli.main` legt ihr Farbsystem beim Import fest. Mit
`FORCE_COLOR` oder bei `pytest -s` in einem echten Terminal schrieb sie Farbcodes
in die Ausgabe des CliRunner, und Tests, die Klartext vergleichen, scheiterten.
`tests/conftest.py` setzt deshalb `TTY_COMPATIBLE=0`, bevor sdd_cli importiert
wird.

Die Probe prüft die echte Console. Die Wächter führen sie in einem frischen
pytest-Prozess aus, unter genau den Bedingungen, die vorher scheiterten.
"""
from __future__ import annotations

import os
import subprocess
import sys
import threading
from pathlib import Path

import pytest

# Auf Modulebene, wie in den Tests, die scheiterten: Die Console entsteht dann bei
# der Sammlung. Bei `-s` ist stdout zu dem Zeitpunkt das Terminal. Im Testkörper
# hätte capsys stdout schon ersetzt, und die Probe bliebe auch ohne Korrektur grün.
from sdd_cli.main import console

_ROOT = Path(__file__).resolve().parents[2]
_SONDE = f"{Path(__file__).relative_to(_ROOT)}::test_sonde_cli_ausgabe_ohne_farbcodes"

# Was eine farbfreudige Shell mitbringt. TTY_COMPATIBLE=1 prüft zugleich, dass
# der conftest einen Wert aus der Shell überschreibt. Das TTY_COMPATIBLE=0, das
# dieser Prozess geerbt hat, ist damit ebenfalls weg.
_FARBIGE_SHELL = {"FORCE_COLOR": "3", "TTY_COMPATIBLE": "1",
                  "TERM": "xterm-256color", "COLORTERM": "truecolor"}


def test_sonde_cli_ausgabe_ohne_farbcodes(capsys):
    console.print("[bold green]✓[/] Projekt [bold]PRJ-0001[/bold]")
    ausgabe = capsys.readouterr().out
    assert "\x1b[" not in ausgabe, repr(ausgabe)
    assert "✓ Projekt PRJ-0001" in ausgabe


def _pytest_argv(*extra: str) -> list[str]:
    return [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *extra, _SONDE]


def test_sonde_besteht_bei_force_color():
    env = {**os.environ, **_FARBIGE_SHELL}
    lauf = subprocess.run(_pytest_argv(), cwd=_ROOT, env=env,
                          capture_output=True, text=True, timeout=120)
    assert lauf.returncode == 0, lauf.stdout + lauf.stderr


@pytest.mark.skipif(sys.platform == "win32", reason="braucht ein Pseudo-Terminal")
def test_sonde_besteht_mit_s_im_echten_terminal():
    """`pytest -s` im Terminal: Die Console sieht beim Import ein TTY."""
    import pty

    master, slave = pty.openpty()
    gelesen: list[bytes] = []

    def lesen():
        while True:
            try:
                block = os.read(master, 4096)
            except OSError:
                return
            if not block:
                return
            gelesen.append(block)

    leser = threading.Thread(target=lesen, daemon=True)
    leser.start()
    env = {**os.environ, "TERM": "xterm-256color", "COLORTERM": "truecolor"}
    for name in ("FORCE_COLOR", "TTY_COMPATIBLE"):
        env.pop(name, None)
    try:
        lauf = subprocess.run(_pytest_argv("-s"), cwd=_ROOT, env=env,
                              stdin=slave, stdout=slave, stderr=slave, timeout=120)
    finally:
        os.close(slave)
        leser.join(timeout=10)
        os.close(master)
    ausgabe = b"".join(gelesen).decode(errors="replace")
    assert lauf.returncode == 0, ausgabe
