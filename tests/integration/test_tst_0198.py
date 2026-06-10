"""TST-0198 – Verantwortlichkeitstrennung review contract vs test generate (Integration)
Spec: SPEC-0044 · Contract: CON-0170
Prüft dass sdd review contract keine TST-Dateien anlegt und sdd test generate existiert.
"""
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SDD_TESTS_DIR = REPO_ROOT / ".sdd" / "tests"


def _run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["sdd"] + args,
        capture_output=True, text=True, cwd=REPO_ROOT
    )


def _count_tst_files() -> int:
    return len(list(SDD_TESTS_DIR.rglob("TST-*.md")))


def test_review_contract_creates_no_tst_files():
    count_before = _count_tst_files()
    _run(["review", "contract", "CON-0165"])
    count_after = _count_tst_files()
    assert count_after == count_before, (
        f"sdd review contract hat TST-Dateien angelegt: "
        f"vorher {count_before}, nachher {count_after}"
    )


def test_test_generate_command_exists():
    result = _run(["test", "generate", "--help"])
    assert result.returncode == 0, \
        "sdd test generate --help muss Exit 0 liefern (Befehl muss existieren)"
