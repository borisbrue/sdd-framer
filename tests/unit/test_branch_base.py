"""`sdd start` zweigte immer von `main` ab.

`dev_container.py` rief fest `git checkout -b dev/<SPEC> main`. Steht die Arbeit
einer noch nicht gemergten Vorgaenger-Spec auf einem Feature-Branch, entsteht
der Entwicklungszweig ohne sie.

Zweite Folge: `sdd start` schreibt vorher den Spec-Status und das audit.log. Wer
nicht auf main stand, bekam beim Wechsel auf mains Baum

    Bitte committen oder stashen Sie Ihre Änderungen, bevor Sie Branches wechseln.
    ✗ Runtime-Fehler – Rollback abgeschlossen

— an Aenderungen, die `sdd start` selbst erzeugt hatte.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tool"))

# Lazy, damit die Verhaltenstests auch gegen einen Stand ohne die neue
# Funktion laufen und der RED-Nachweis nicht auf einen Collection-Error
# zusammenfaellt.


def resolve_base_branch(cfg_raw):
    from sdd_cli.dev_container import resolve_base_branch as _impl
    return _impl(cfg_raw)


def _repo(tmp_path: Path) -> Path:
    for args in (["init", "-q", "-b", "main"], ["config", "user.email", "b@e.de"],
                 ["config", "user.name", "B"]):
        subprocess.run(["git", *args], cwd=tmp_path, capture_output=True)
    (tmp_path / "a.txt").write_text("eins\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=tmp_path, capture_output=True)
    return tmp_path


def _git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)


class TestAbzweigpunkt:
    def test_ohne_angabe_head(self):
        assert resolve_base_branch({}) is None
        assert resolve_base_branch({"docker": {}}) is None

    def test_konfigurierter_wert_sticht(self):
        assert resolve_base_branch({"docker": {"base_branch": "main"}}) == "main"

    def test_leerer_wert_zaehlt_als_nicht_gesetzt(self):
        assert resolve_base_branch({"docker": {"base_branch": ""}}) is None


class TestVorgaengerarbeitBleibtErhalten:
    def test_head_traegt_die_arbeit_der_vorgaengerspec(self, tmp_path):
        """Der gemeldete Fall: SPEC-0003 baut auf ungemergtem feat/SPEC-0002 auf."""
        root = _repo(tmp_path)
        _git(root, "checkout", "-q", "-b", "feat/SPEC-0002")
        (root / "vorgaenger.py").write_text("x = 1\n", encoding="utf-8")
        _git(root, "add", "-A")
        _git(root, "commit", "-q", "-m", "SPEC-0002")

        # Von HEAD: die Arbeit ist dabei.
        _git(root, "checkout", "-q", "-b", "dev/SPEC-0003")
        assert (root / "vorgaenger.py").exists()

    def test_von_main_fehlt_sie(self, tmp_path):
        """Das alte Verhalten, zum Vergleich."""
        root = _repo(tmp_path)
        _git(root, "checkout", "-q", "-b", "feat/SPEC-0002")
        (root / "vorgaenger.py").write_text("x = 1\n", encoding="utf-8")
        _git(root, "add", "-A")
        _git(root, "commit", "-q", "-m", "SPEC-0002")

        _git(root, "checkout", "-q", "-b", "dev/SPEC-0003", "main")
        assert not (root / "vorgaenger.py").exists()


class TestUncommitteteAenderungenUeberleben:
    def test_von_head_kein_konflikt(self, tmp_path):
        """`sdd start` schreibt Spec-Status und audit.log vor dem Branchwechsel."""
        root = _repo(tmp_path)
        _git(root, "checkout", "-q", "-b", "feat/SPEC-0002")
        (root / "a.txt").write_text("geaendert durch sdd start\n", encoding="utf-8")

        ergebnis = _git(root, "checkout", "-b", "dev/SPEC-0003")

        assert ergebnis.returncode == 0, ergebnis.stderr
        assert (root / "a.txt").read_text(encoding="utf-8").startswith("geaendert")

    def test_von_main_scheitert(self, tmp_path):
        """Genau die gemeldete Fehlermeldung."""
        root = _repo(tmp_path)
        _git(root, "checkout", "-q", "-b", "feat/SPEC-0002")
        (root / "a.txt").write_text("auf dem Branch geaendert\n", encoding="utf-8")
        _git(root, "add", "-A")
        _git(root, "commit", "-q", "-m", "branch-stand")
        (root / "a.txt").write_text("geaendert durch sdd start\n", encoding="utf-8")

        ergebnis = _git(root, "checkout", "-b", "dev/SPEC-0003", "main")
        assert ergebnis.returncode != 0


class TestRollbackKehrtZurueck:
    def test_checkout_minus_statt_main(self):
        """Der Rollback ging pauschal auf main — auch wenn man woanders herkam."""
        import inspect

        from sdd_cli import dev_container
        src = inspect.getsource(dev_container.DevContainerManager.start)
        assert '_git(["checkout", "-"], check=False)' in src
        assert '_git(["checkout", "main"], check=False)' not in src
