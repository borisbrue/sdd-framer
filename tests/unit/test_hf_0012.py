"""HF-0012: Der Implementer bekommt den aktuellen Inhalt der Dateien aus allowed_paths.

Ohne diese Quelle musste die Rolle bestehende Dateien „vollständig liefern“, ohne sie je gesehen
zu haben; beim Erweitern eines Moduls ging bestehender Code verloren (Testprojekt todo-service,
SPEC-0002: TodoNotFoundError in todo/domain/todo.py ersetzte Todo und ValidationError).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from sdd_cli.pipeline.context import ProjectContext
from sdd_cli.pipeline.roles import CONTEXT_SOURCES, load_role
from sdd_cli.pipeline.runner import SOURCE_TITLES

REPO = Path(__file__).resolve().parents[2]


def _projekt(tmp_path: Path) -> ProjectContext:
    for rel, text in {
        "todo/service/service.py": "class TodoService:\n    pass  # alter Stand\n",
        "todo/service/__init__.py": "from todo.service.service import TodoService\n",
        "todo/domain/todo.py": "class Todo: ...\n",
        "tests/unit/test_service.py": "import unittest\n",
        ".sdd/holdout/geheim.py": "GEHEIM = 1\n",
    }.items():
        pfad = tmp_path / rel
        pfad.parent.mkdir(parents=True, exist_ok=True)
        pfad.write_text(text, encoding="utf-8")
    return ProjectContext(tmp_path, "SPEC-0900")


def test_current_files_zeigt_vorhandene_dateien_aus_allowed_paths(tmp_path):
    ctx = _projekt(tmp_path)
    text = ctx.current_files(["todo/service/*.py", "todo/service/neu.py"],
                             exclude=["tests/unit/test_service.py"])
    assert "### todo/service/service.py" in text and "# alter Stand" in text
    assert "### todo/service/__init__.py" in text
    assert "todo/domain/todo.py" not in text
    assert "neu.py" not in text


def test_current_files_ohne_testdatei_sdd_und_holdout(tmp_path):
    ctx = _projekt(tmp_path)
    text = ctx.current_files(["**/*.py"], exclude=["tests/unit/test_service.py"])
    assert "tests/unit/test_service.py" not in text
    assert ".sdd" not in text and "GEHEIM" not in text
    assert "todo/domain/todo.py" in text


def test_current_files_leer_wenn_nichts_existiert(tmp_path):
    ctx = _projekt(tmp_path)
    assert ctx.current_files(["gibt/es/nicht.py"], exclude=[]) == ""


def test_quelle_ist_registriert_und_betitelt():
    assert "current_files" in CONTEXT_SOURCES
    assert SOURCE_TITLES["current_files"]


def test_implementer_rolle_nutzt_die_quelle():
    rolle = load_role(REPO, "implementer")
    assert "current_files" in rolle.inputs
    assert rolle.budget("current_files") >= 8000
    assert "current_files" in rolle.prompt


@pytest.mark.parametrize("schema", [
    REPO / ".sdd/contracts/data/rollendefinition-frontmatter-von-sdd-roles-rolle-md.schema.json",
    REPO / "tool/sdd_cli/pipeline/schemas/role-definition.schema.json",
])
def test_rollenschema_kennt_die_quelle(schema):
    text = json.dumps(json.loads(schema.read_text(encoding="utf-8")))
    assert text.count('"current_files"') >= 2  # inputs und input_budgets


# ── Ende zu Ende: der Implementer-Prompt enthält den bestehenden Stand ──────────

@pytest.fixture()
def llm():
    from tests.support.fake_llm import FakeLLM

    fake = FakeLLM().start()
    yield fake
    fake.stop()


def test_implementer_prompt_enthaelt_bestehende_datei(tmp_path, monkeypatch, llm):
    from tests.support.fake_llm import prompt_text
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

    projekt = make_pipeline_project(tmp_path, monkeypatch, llm, frs=("FR-01",))
    (projekt.root / "src/start.sh").write_text('echo "alt"  # bestehender-stand-hf0012\n')
    t1 = task("Start", ["FR-01"], "src/start.sh")
    llm.antworte("decomposer", zerlegung(t1))
    llm.antworte("supervisor", command("S1", "approve"), abnahme(FR_01="erfüllt"))
    llm.antworte("test_author", rot_test(t1))
    llm.antworte("implementer", implementierung(t1))
    llm.antworte("reviewer", review())
    ergebnis = projekt.run("pipeline", "run", "SPEC-0900")
    assert ergebnis.exit_code == 0, ergebnis.output
    [aufruf] = llm.aufrufe("implementer")
    text = prompt_text(aufruf)
    assert "### src/start.sh" in text and "bestehender-stand-hf0012" in text
    abschnitt = re.search(r"^## Aktueller Inhalt[^\n]*\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    assert abschnitt is not None
    assert "bestehender-stand-hf0012" in abschnitt.group(1)
    assert "### tests/" not in abschnitt.group(1)
