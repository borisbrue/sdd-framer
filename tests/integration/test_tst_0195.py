"""TST-0195 – Top-Level-Befehle in Gruppen sdd spec und sdd autonomy (Integration)
Spec: SPEC-0044 · Contract: CON-0167
Prüft neue Gruppen-Befehle und dass sdd status-check nicht mehr öffentlich ist.
"""
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["sdd"] + args,
        capture_output=True, text=True, cwd=REPO_ROOT
    )


def test_spec_solid_available():
    result = _run(["spec", "solid", "--help"])
    assert result.returncode == 0, "sdd spec solid --help muss Exit 0 liefern"


def test_spec_regression_available():
    result = _run(["spec", "regression", "--help"])
    assert result.returncode == 0, "sdd spec regression --help muss Exit 0 liefern"


def test_autonomy_level_available():
    result = _run(["autonomy", "level", "--help"])
    assert result.returncode == 0, "sdd autonomy level --help muss Exit 0 liefern"


def test_autonomy_set_level_available():
    result = _run(["autonomy", "set-level", "--help"])
    assert result.returncode == 0, "sdd autonomy set-level --help muss Exit 0 liefern"


def test_autonomy_false_positive_available():
    result = _run(["autonomy", "false-positive", "--help"])
    assert result.returncode == 0, "sdd autonomy false-positive --help muss Exit 0 liefern"


def test_status_check_not_public():
    result = _run(["status-check"])
    assert result.returncode != 0, \
        "sdd status-check darf nach Cleanup nicht mehr als öffentlicher Befehl verfügbar sein"
    combined = result.stdout + result.stderr
    assert combined.strip(), "Fehlermeldung darf nicht leer sein"
