"""TST-0194 – Kanonische Verb-Gruppen `sdd new` und `sdd review` (Integration)
Spec: SPEC-0044 · Contract: CON-0166
Prüft neue kanonische Befehle und dass alte Formen Migrationshinweise geben.
"""
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["sdd"] + args,
        capture_output=True, text=True, cwd=REPO_ROOT
    )


def test_new_hotfix_available():
    result = _run(["new", "hotfix", "--help"])
    assert result.returncode == 0, "sdd new hotfix --help muss Exit 0 liefern"


def test_review_spec_available():
    result = _run(["review", "spec", "--help"])
    assert result.returncode == 0, "sdd review spec --help muss Exit 0 liefern"


def test_review_contract_available():
    result = _run(["review", "contract", "--help"])
    assert result.returncode == 0, "sdd review contract --help muss Exit 0 liefern"


def test_review_pending_available():
    result = _run(["review", "pending", "--help"])
    assert result.returncode == 0, "sdd review pending --help muss Exit 0 liefern"


def test_holdout_generate_available():
    result = _run(["holdout", "generate", "--help"])
    assert result.returncode == 0, "sdd holdout generate --help muss Exit 0 liefern"


def test_test_run_available():
    result = _run(["test", "run", "--help"])
    assert result.returncode == 0, "sdd test run --help muss Exit 0 liefern"


def test_contract_analyze_available():
    result = _run(["contract", "analyze", "--help"])
    assert result.returncode == 0, "sdd contract analyze --help muss Exit 0 liefern"


def test_old_generate_holdouts_gives_migration_hint():
    result = _run(["generate-holdouts", "SPEC-0044"])
    assert result.returncode != 0, "sdd generate-holdouts muss nach Cleanup fehlschlagen"
    combined = (result.stdout + result.stderr).lower()
    assert "holdout generate" in combined, \
        "Fehlerausgabe muss auf 'sdd holdout generate' hinweisen"


def test_old_evaluate_gives_migration_hint():
    result = _run(["evaluate"])
    assert result.returncode != 0, "sdd evaluate muss nach Cleanup fehlschlagen"
    combined = (result.stdout + result.stderr).lower()
    assert "holdout run" in combined, \
        "Fehlerausgabe muss auf 'sdd holdout run' hinweisen"
