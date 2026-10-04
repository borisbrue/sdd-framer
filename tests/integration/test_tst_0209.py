"""TST-0209 – Verantwortlichkeitstrennung review contract vs test generate (Integration)
Spec: SPEC-0044 · Contract: CON-0170
Prüft dass sdd review contract keine TST-Dateien anlegt und sdd test generate existiert.

Der Lauf findet in einem Wegwerf-Projekt statt. Vorher rief er
`sdd review contract CON-0165` mit cwd=REPO_ROOT auf — also gegen das echte
Repository. Der Review haengt seine Notizen an die Contract-Datei an, sodass
jeder Testlauf .sdd/contracts/behavior/CON-0165-cli-gruppen-entfernt.md
veraenderte und den Arbeitsbaum schmutzig hinterliess.
"""
import subprocess
from pathlib import Path

import pytest


def _run(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["sdd"] + args,
        capture_output=True, text=True, cwd=cwd, timeout=300,
    )


def _count_tst_files(root: Path) -> int:
    return len(list((root / ".sdd" / "tests").rglob("TST-*.md")))


@pytest.fixture
def projekt(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, capture_output=True)
    _run(["init", "--name", "TST-0209"], tmp_path)
    _run(["new", "spec", "Beispiel"], tmp_path)
    _run(["new", "contract", "--spec", "SPEC-0001", "--format", "gherkin",
          "--title", "Beispiel"], tmp_path)
    return tmp_path


def test_review_contract_creates_no_tst_files(projekt: Path):
    """Die Invariante gilt unabhaengig davon, ob der Review durchlaeuft.

    Genau das ist der Punkt: `sdd review contract` darf keine TST-Dateien
    anlegen — weder bei Erfolg noch bei Fehlschlag. Zustaendig dafuer ist
    `sdd test generate`.
    """
    count_before = _count_tst_files(projekt)
    assert count_before >= 1, "sdd new contract legt einen Test-Stub an"

    _run(["review", "contract", "CON-0001"], projekt)

    assert _count_tst_files(projekt) == count_before, (
        f"sdd review contract hat TST-Dateien angelegt: "
        f"vorher {count_before}, nachher {_count_tst_files(projekt)}"
    )


def test_test_generate_command_exists(tmp_path: Path):
    result = _run(["test", "generate", "--help"], tmp_path)
    assert result.returncode == 0, \
        "sdd test generate --help muss Exit 0 liefern (Befehl muss existieren)"
