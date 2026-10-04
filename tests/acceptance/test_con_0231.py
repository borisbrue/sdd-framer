# AUTO-GENERATED from CON-0231 via sdd test generate — do not delete
"""Contract-Tests für Rollenkontext beim Erweitern (CON-0231).

Spec: SPEC-0065 · Contract: CON-0231
Die Pipeline-Szenarien laufen mit Fake-Rollen (braucht `openai`, sonst übersprungen); Quellen,
Extraktor, Rollen, Check und Golden Cases werden direkt geprüft.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from sdd_cli.pipeline.context import ProjectContext
from sdd_cli.pipeline.roles import CONTEXT_SOURCES, load_role

REPO = Path(__file__).resolve().parents[2]
BLUEPRINT = REPO / "tool/sdd_cli/blueprint"

STORAGE = '''"""Ablage."""


class Store:
    """Speichert Einträge."""

    def __init__(self, path: str) -> None:
        self._path = path

    def save(self) -> None:
        """Schreibt atomar."""
        geheim = "RUMPF-INHALT"
        print(geheim)

    def _intern(self) -> int:
        return 1


def load_all(path: str, *, strict: bool = False) -> list[dict]:
    """Lädt alles."""
    return []


def _helper() -> None:
    pass
'''


def _schreibe(root: Path, dateien: dict[str, str]) -> None:
    for rel, text in dateien.items():
        pfad = root / rel
        pfad.parent.mkdir(parents=True, exist_ok=True)
        pfad.write_text(text, encoding="utf-8")


def _abschnitt(text: str, titel: str) -> str:
    treffer = re.search(rf"^## {re.escape(titel)}[^\n]*\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    return treffer.group(1) if treffer else ""


# ── Extraktor und dependency_api (INV-02, INV-03) ──────────────────────────────

def test_python_extraktor_liefert_oeffentliche_signaturen_ohne_rumpf():
    from sdd_cli.pipeline.signatures import api_of

    text = api_of("src/storage.py", STORAGE)
    assert "class Store" in text and "Speichert Einträge." in text
    assert "def __init__(self, path: str) -> None" in text
    assert "def save(self) -> None" in text and "Schreibt atomar." in text
    assert "def load_all(path: str, *, strict: bool=False) -> list[dict]" in text
    assert "RUMPF-INHALT" not in text
    assert "_intern" not in text and "_helper" not in text


def test_python_extraktor_zeigt_felder_konstanten_und_dekoratoren():
    from sdd_cli.pipeline.signatures import api_of

    text = api_of("todo/domain.py", '''
from dataclasses import dataclass

MAX_TITLE = 200
_INTERN = 1
LANG = "%s"


@dataclass(frozen=True)
class Todo:
    id: int
    done: bool = False
    _cache: dict | None = None
''' % ("x" * 100))
    assert "MAX_TITLE = 200" in text and "LANG = ..." in text and "_INTERN" not in text
    assert "@dataclass(frozen=True)\nclass Todo:" in text
    assert "    id: int" in text and "    done: bool = False" in text and "_cache" not in text


def test_datei_ohne_extraktor_nur_mit_pfad():
    from sdd_cli.pipeline.signatures import api_of

    text = api_of("config/app.toml", "geheim = 1\n")
    assert "geheim" not in text and "kein Extraktor" in text


def test_syntaxfehler_nur_mit_hinweis():
    from sdd_cli.pipeline.signatures import api_of

    text = api_of("src/kaputt.py", "def x(:\n")
    assert "nicht lesbar" in text


def test_registry_ist_erweiterbar():
    from sdd_cli.pipeline import signatures

    signatures.register(".demo", lambda text: ["demo-signatur"])
    try:
        assert "demo-signatur" in signatures.api_of("a.demo", "")
    finally:
        signatures.EXTRACTORS.pop(".demo")


def test_dependency_api_aus_erledigten_abhaengigkeiten(tmp_path):
    _schreibe(tmp_path, {"src/storage.py": STORAGE, "src/notizen.txt": "frei\n",
                         "tests/test_storage.py": "def test_x(): pass\n",
                         ".sdd/holdout/geheim.py": "def geheim(): pass\n"})
    ctx = ProjectContext(tmp_path, "SPEC-0900")
    t01 = {"id": "T01", "title": "Ablage", "allowed_paths": ["src/*", ".sdd/holdout/*"],
           "test_file": "tests/test_storage.py"}
    text = ctx.dependency_api([t01])
    assert "### src/storage.py (T01 Ablage)" in text
    assert "def save(self) -> None" in text and "RUMPF-INHALT" not in text
    assert "### src/notizen.txt (T01 Ablage)" in text and "kein Extraktor" in text
    assert "geheim" not in text and "test_storage" not in text
    assert ctx.dependency_api([]) == ""


def test_pipeline_kern_nennt_keine_sprache():
    for datei in ("context.py", "mediator.py", "signatures.py"):
        text = (REPO / "tool/sdd_cli/pipeline" / datei).read_text(encoding="utf-8")
        code = "\n".join(z for z in text.splitlines() if not z.lstrip().startswith("#"))
        assert not re.search(r"\bpython\b|\bimport ast\b", code, re.I), datei


# ── Rollen (INV-01, INV-04, INV-05, INV-06) ────────────────────────────────────

def test_inv01_quellen_der_rollen():
    assert "dependency_api" in CONTEXT_SOURCES
    autor = load_role(REPO, "test_author")
    implementer = load_role(REPO, "implementer")
    assert {"current_files", "dependency_api"} <= set(autor.inputs)
    assert {"current_files", "dependency_api"} <= set(implementer.inputs)


def test_inv04_budgets():
    autor = load_role(REPO, "test_author")
    assert autor.budget("current_files") == 8000 and autor.budget("dependency_api") == 4000
    assert load_role(REPO, "implementer").budget("dependency_api") == 4000


def test_inv05_decomposer_kennt_pruef_tasks():
    text = load_role(REPO, "decomposer").prompt
    assert "`test`" in text and "absichern" in text


def test_inv06_regeln_des_test_autors():
    text = load_role(REPO, "test_author").prompt
    assert "current_files" in text and "dependency_api" in text and "Mock" in text


def test_check_task_type_present():
    from sdd_cli.pipeline.checks import CheckEnv, run_check

    zerlegung = {"tasks": [{"type": "code"}, {"type": "test"}]}
    assert not run_check("task_type_present", CheckEnv(output=zerlegung,
                                                       params={"type": "test", "min": 1})).failed
    assert run_check("task_type_present", CheckEnv(output={"tasks": [{"type": "code"}]},
                                                   params={"type": "test", "min": 1})).failed


@pytest.mark.parametrize("fall", ["decomposer/cases/DEC-009", "test_author/cases/TAU-009"])
def test_golden_cases_vorhanden(fall):
    rolle, _, praefix = fall.split("/")
    treffer = list((BLUEPRINT / "roles" / rolle / "cases").glob(f"{praefix}-*"))
    assert treffer, fall
    case = (treffer[0] / "case.yaml").read_text(encoding="utf-8")
    assert f"id: {praefix}" in case
    if rolle == "decomposer":
        assert "task_type_present" in case
    else:
        assert (treffer[0] / "input/current_files.md").is_file()
        assert (treffer[0] / "input/dependency_api.md").is_file()


# ── Ende zu Ende mit Fake-Rollen (Szenarien) ───────────────────────────────────

@pytest.fixture()
def llm():
    from tests.support.fake_llm import FakeLLM

    fake = FakeLLM().start()
    yield fake
    fake.stop()


def _lauf(tmp_path, monkeypatch, llm, *, t2_offen=False):
    from tests.support.pipeline_project import (
        abnahme,
        command,
        implementierung,
        make_pipeline_project,
        review,
        rot_test,
        task,
        zerlegung,
    )

    projekt = make_pipeline_project(tmp_path, monkeypatch, llm, frs=("FR-01", "FR-02"))
    (projekt.root / "src/start.sh").write_text('echo "alt"  # bestehender-stand-con0231\n')
    t1 = task("Start", ["FR-01"], "src/start.sh")
    t2 = task("Stop", ["FR-02"], "src/stop.sh", deps=["Start"])
    llm.antworte("decomposer", zerlegung(t1, t2))
    llm.antworte("supervisor", command("S1", "approve"),
                 abnahme(FR_01="erfüllt", FR_02="erfüllt"))
    llm.antworte("test_author", rot_test(t1), rot_test(t2))
    llm.antworte("implementer", implementierung(t1), implementierung(t2))
    llm.antworte("reviewer", review(), review())
    return projekt, projekt.run("pipeline", "run", "SPEC-0900")


def test_tc01_test_autor_sieht_bestehenden_code(tmp_path, monkeypatch, llm):
    """Scenario: Test-Autor sieht bestehenden Code (CON-0231)."""
    from tests.support.fake_llm import prompt_text

    _, ergebnis = _lauf(tmp_path, monkeypatch, llm)
    assert ergebnis.exit_code == 0, ergebnis.output
    erster = prompt_text(llm.aufrufe("test_author")[0])
    abschnitt = _abschnitt(erster, "Aktueller Inhalt")
    assert "bestehender-stand-con0231" in abschnitt
    assert "### tests/" not in abschnitt


def test_tc02_schnittstellen_einer_erledigten_abhaengigkeit(tmp_path, monkeypatch, llm):
    """Scenario: Schnittstellen einer erledigten Abhängigkeit (CON-0231)."""
    from tests.support.fake_llm import prompt_text

    _, ergebnis = _lauf(tmp_path, monkeypatch, llm)
    assert ergebnis.exit_code == 0, ergebnis.output
    zweiter_impl = prompt_text(llm.aufrufe("implementer")[1])
    api = _abschnitt(zweiter_impl, "Schnittstellen")
    assert "### src/start.sh (T01 Start)" in api
    zweiter_autor = prompt_text(llm.aufrufe("test_author")[1])
    assert "src/start.sh" in _abschnitt(zweiter_autor, "Schnittstellen")


def test_tc03_abhaengigkeit_noch_offen(tmp_path, monkeypatch, llm):
    """Scenario: Abhängigkeit noch offen (CON-0231)."""
    from tests.support.fake_llm import prompt_text

    _lauf(tmp_path, monkeypatch, llm)
    erster_autor = prompt_text(llm.aufrufe("test_author")[0])
    assert "(T01" not in _abschnitt(erster_autor, "Schnittstellen")


def test_tc04_datei_ohne_extraktor(tmp_path):
    """Scenario: Datei ohne Extraktor (CON-0231)."""
    _schreibe(tmp_path, {"config/app.toml": "schluessel = 1\n"})
    text = ProjectContext(tmp_path, "SPEC-0900").dependency_api(
        [{"id": "T01", "title": "Konfig", "allowed_paths": ["config/*"]}])
    assert "### config/app.toml (T01 Konfig)" in text and "schluessel" not in text


def test_tc05_kuerzung_nach_budget():
    """Scenario: Kürzung nach Budget (CON-0231)."""
    from sdd_cli.pipeline.runner import truncate

    gekuerzt = truncate("x" * 40000, 8000)
    assert gekuerzt.endswith("[gekürzt auf etwa 8000 Tokens]")


def test_tc06_pruef_task_als_test():
    """Scenario: Prüf-Task als test (CON-0231) – die Regel steht in der Rolle, DEC-009 prüft sie."""
    text = load_role(REPO, "decomposer").prompt
    assert re.search(r"nur bestehendes Verhalten absichern.*`test`", text, re.S)
