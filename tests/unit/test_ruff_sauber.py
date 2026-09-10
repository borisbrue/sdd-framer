"""Das Repository bleibt ruff-sauber (#112).

Vor der Bereinigung meldete `ruff check .` 890 Fehler — darunter echte: ein
nicht importiertes Modul, dessen NameError ein `except` verschluckte, sodass die
Live-Logs im Web-UI nie liefen. Solche Fehler findet ruff zuverlaessig, aber nur,
wenn jemand hinsieht. Dieser Test sieht hin.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]


def _ruff() -> str | None:
    # Zuerst das Projekt-venv (dependency-groups dev), dann der PATH.
    kandidat = Path(sys.executable).parent / "ruff"
    return str(kandidat) if kandidat.exists() else shutil.which("ruff")


def test_ruff_check_ist_sauber():
    ruff = _ruff()
    if not ruff:
        pytest.skip("ruff nicht verfuegbar — `uv sync` installiert es mit der dev-Gruppe")
    ergebnis = subprocess.run(
        [ruff, "check", "--no-cache", "--output-format=concise", "."],
        cwd=_ROOT, capture_output=True, text=True,
    )
    assert ergebnis.returncode == 0, (
        "ruff meldet Fehler:\n" + ergebnis.stdout[-4000:]
    )


def test_konfiguration_begruendet_jede_ausnahme():
    """Eine Regel abzuschalten ist erlaubt — stillschweigend nicht."""
    import tomllib

    daten = tomllib.loads((_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    ignoriert = daten["tool"]["ruff"]["lint"].get("ignore", [])
    text = (_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    ohne_grund = [r for r in ignoriert if f"# {r}:" not in text]
    assert not ohne_grund, f"ignorierte Regeln ohne Begruendungskommentar: {ohne_grund}"
