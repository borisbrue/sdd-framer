# AUTO-GENERATED from CON-0209 via sdd test generate — do not delete
"""TST-0238 – CON-0209: Architekturprüfung für sdd-framer und Pre-Commit-Hook.

Spec: SPEC-0059 · Contract: CON-0209
Szenarien auf dem Repo-Stand laufen gegen den Arbeitsbaum (nur lesend); Szenarien, die einen
Verstoß einbauen, arbeiten auf einer Kopie in tmp_path.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import time
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

REPO = Path(__file__).resolve().parents[2]
REGELN = ("ARCH-01", "ARCH-02", "ARCH-03", "ARCH-04")
KOPIE_IGNORIEREN = shutil.ignore_patterns("node_modules", "dist", "__pycache__", ".venv",
                                          "*.egg-info", "holdout", "runs", "evaluations.db")


def _arch_check(root: Path, monkeypatch) -> tuple[int, str]:
    from sdd_cli.main import cli

    monkeypatch.chdir(root)
    ergebnis = CliRunner().invoke(cli, ["arch", "check"])
    return ergebnis.exit_code, ergebnis.output


@pytest.fixture(scope="module")
def repo_lauf():
    """Ein Lauf von `sdd arch check` auf dem Repo-Stand (für tc01 und tc10)."""
    from sdd_cli.main import cli

    mp = pytest.MonkeyPatch()
    mp.chdir(REPO)
    start = time.monotonic()
    ergebnis = CliRunner().invoke(cli, ["arch", "check"])
    dauer = time.monotonic() - start
    mp.undo()
    return ergebnis.exit_code, ergebnis.output, dauer


@pytest.fixture()
def kopie(tmp_path):
    """Minimale Kopie des Repos: Code, Architektur, Sonden, ADRs, Konfiguration."""
    shutil.copytree(REPO / "tool" / "sdd_cli", tmp_path / "tool" / "sdd_cli",
                    ignore=KOPIE_IGNORIEREN)
    (tmp_path / ".sdd").mkdir()
    for name in ("architecture.yaml", "quality.yaml", "config.yaml"):
        shutil.copy(REPO / ".sdd" / name, tmp_path / ".sdd" / name)
    shutil.copytree(REPO / ".sdd" / "quality", tmp_path / ".sdd" / "quality")
    shutil.copytree(REPO / "docs" / "adr", tmp_path / "docs" / "adr")
    return tmp_path


def test_tc01_main_ist_gruen_trotz_altlasten(repo_lauf):
    """Scenario: Main ist grün trotz Altlasten (CON-0209)."""
    exit_code, ausgabe, _ = repo_lauf
    assert exit_code == 0, ausgabe
    # Der CodeGen-Pfad in openai_compat.py ist seit SPEC-0062 entfernt, sein Baseline-Eintrag mit.
    treffer = [z for z in ausgabe.splitlines()
               if "ARCH-01" in z and "tool/sdd_cli/llm/providers/openai_compat.py" in z]
    assert not treffer, ausgabe


def test_tc02_jede_regel_ist_an_ein_akzeptiertes_adr_gebunden():
    """Scenario: Jede Regel ist an ein akzeptiertes ADR gebunden (CON-0209)."""
    from sdd_cli.config import load_config
    from sdd_cli.frontmatter import parse
    from sdd_cli.validate import validate

    arch = yaml.safe_load((REPO / ".sdd/architecture.yaml").read_text(encoding="utf-8"))
    regeln = {r["id"]: r["adr"] for r in arch["rules"]}
    assert set(REGELN) <= set(regeln)  # spätere Specs ergänzen Regeln (SPEC-0062: ARCH-05)
    for regel, adr in regeln.items():
        [datei] = (REPO / "docs/adr").glob(f"{adr}-*.md")
        fm = parse(datei).frontmatter
        assert fm["status"] == "accepted", adr
        assert regel in fm.get("enforced_by", []), adr
    betroffen = {REPO / ".sdd/architecture.yaml", *(REPO / "docs/adr").glob("ADR-*.md")}
    fehler = [i.message for i in validate(load_config(REPO)).issues
              if i.severity == "error" and i.file in betroffen]
    assert fehler == []


def test_tc03_die_baseline_enthaelt_keinen_arch_03_eintrag():
    """Scenario: Die Baseline enthält keinen ARCH-03-Eintrag (CON-0209)."""
    baseline = json.loads((REPO / ".sdd/quality/arch-baseline.json").read_text(encoding="utf-8"))
    assert baseline["entries"], "Baseline ist leer"
    assert not [e for e in baseline["entries"] if e["rule"] == "ARCH-03"]
    for e in baseline["entries"]:
        assert e["reason"].strip() and "TODO" not in e["reason"], e


def test_tc04_neuer_verstoss_blockiert(kopie, monkeypatch):
    """Scenario: Neuer Verstoß blockiert (CON-0209)."""
    neu = kopie / "tool/sdd_cli/web/api/routes/new.py"
    neu.write_text("from sdd_cli.llm.providers.openai_compat import OpenAICompatCompletionProvider\n",
                   encoding="utf-8")
    exit_code, ausgabe = _arch_check(kopie, monkeypatch)
    assert exit_code == 1, ausgabe
    zeile = next(z for z in ausgabe.splitlines() if "routes/new.py" in z)
    assert "ARCH-03" in zeile and "ADR-0004" in zeile


def test_tc05_unaufgeloester_schreibzugriff_aus_der_web_api(kopie, monkeypatch):
    """Scenario: Unaufgelöster Schreibzugriff aus der Web-API (CON-0209)."""
    neu = kopie / "tool/sdd_cli/web/api/routes/new.py"
    neu.write_text("from pathlib import Path\n\n\ndef speichern(ziel, text):\n"
                   "    Path(ziel).write_text(text)\n", encoding="utf-8")
    exit_code, ausgabe = _arch_check(kopie, monkeypatch)
    assert exit_code == 1, ausgabe
    zeile = next(z for z in ausgabe.splitlines() if "routes/new.py" in z)
    assert "ARCH-01" in zeile and "pathlib.Path.write_text" in zeile


def test_tc06_ohne_option_bleibt_write_ownership_beim_alten_verh(kopie, monkeypatch):
    """Scenario: Ohne Option bleibt write_ownership beim alten Verhalten (CON-0209)."""
    pfad = kopie / ".sdd/architecture.yaml"
    arch = yaml.safe_load(pfad.read_text(encoding="utf-8"))
    for regel in arch["rules"]:
        regel.pop("unresolved", None)
    pfad.write_text(yaml.safe_dump(arch, sort_keys=False), encoding="utf-8")
    (kopie / "tool/sdd_cli/web/api/routes/new.py").write_text(
        "from pathlib import Path\n\n\ndef speichern(ziel, text):\n"
        "    Path(ziel).write_text(text)\n", encoding="utf-8")
    _, ausgabe = _arch_check(kopie, monkeypatch)
    assert not [z for z in ausgabe.splitlines() if "routes/new.py" in z]


# ── Pre-Commit-Hook ──────────────────────────────────────────────────────────

VERSTOSS = "from app.llm.providers.openai_compat import OpenAICompatCompletionProvider\n"


def _hook_projekt(root: Path, *, architektur: bool = True, config: dict | None = None) -> None:
    """Kleines Git-Projekt mit Importsonde; eine gestagte Datei verletzt ARCH-03."""
    from sdd_cli.main import cli

    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    (root / ".sdd").mkdir()
    (root / ".sdd/config.yaml").write_text(yaml.safe_dump(config or {"version": "1"}),
                                          encoding="utf-8")
    mp = pytest.MonkeyPatch()
    mp.chdir(root)
    CliRunner().invoke(cli, ["quality", "init", "--preset", "python"])
    mp.undo()
    qpfad = root / ".sdd/quality.yaml"
    quality = yaml.safe_load(qpfad.read_text(encoding="utf-8"))
    quality["probes"] = {"imports": quality["probes"]["imports"]}
    qpfad.write_text(yaml.safe_dump(quality, sort_keys=False), encoding="utf-8")
    for paket in ("app", "app/web", "app/llm", "app/llm/providers"):
        (root / paket).mkdir(parents=True, exist_ok=True)
        (root / paket / "__init__.py").write_text("", encoding="utf-8")
    (root / "app/llm/providers/openai_compat.py").write_text(
        "class OpenAICompatCompletionProvider:\n    pass\n", encoding="utf-8")
    (root / "app/web/routes.py").write_text(VERSTOSS, encoding="utf-8")
    if architektur:
        (root / ".sdd/architecture.yaml").write_text(yaml.safe_dump({
            "version": 1,
            "layers": {"web": ["app/web/**"], "llm": ["app/llm/**"]},
            "rules": [{"id": "ARCH-03", "adr": "ADR-0004", "kind": "forbidden_dependency",
                       "from": ["web"], "to_paths": ["app/llm/providers/**"]}]}),
            encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)


def _hook(root: Path, raw: dict | None = None) -> int:
    from sdd_cli.pre_commit_hook import PreCommitHook

    return PreCommitHook(root, raw or {}).run()


def test_tc07_pre_commit_hook_blockiert_einen_architekturverstos(tmp_path, capsys):
    """Scenario: Pre-Commit-Hook blockiert einen Architekturverstoß (CON-0209)."""
    _hook_projekt(tmp_path)
    assert _hook(tmp_path) == 1
    assert "ARCH-03" in capsys.readouterr().out


def test_tc08_pre_commit_hook_ohne_architekturregeln(tmp_path, capsys):
    """Scenario: Pre-Commit-Hook ohne Architekturregeln (CON-0209)."""
    _hook_projekt(tmp_path, architektur=False)
    assert _hook(tmp_path) == 0
    assert "arch" not in capsys.readouterr().out.lower()


def test_tc09_architekturpruefung_im_hook_abgeschaltet(tmp_path, capsys):
    """Scenario: Architekturprüfung im Hook abgeschaltet (CON-0209)."""
    _hook_projekt(tmp_path)
    assert _hook(tmp_path, {"quality": {"arch_pre_commit": False}}) == 0
    assert "ARCH-03" not in capsys.readouterr().out


def test_tc10_laufzeit_der_pruefung(repo_lauf):
    """Scenario: Laufzeit der Prüfung (CON-0209): unter 10 s auf dem Repo-Stand."""
    _, _, dauer = repo_lauf
    assert dauer < 10, f"sdd arch check brauchte {dauer:.1f} s"
