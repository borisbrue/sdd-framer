"""Test-Hilfe für SPEC-0054: temporäres sdd-Projekt mit Shell-Sonden.

Die Sonden sind Shell-Befehle, die vorbereitete Dateien nach ``{out}`` kopieren. So prüfen die
Tests den Kern von ``sdd quality`` sprachneutral, wie es das Erfolgskriterium von SPEC-0054
verlangt, und brauchen weder pytest-Plugins noch ruff oder mypy im Testprojekt.

Solange ``sdd quality`` und ``sdd arch`` nicht implementiert sind, überspringen die
Verhaltenstests mit ``requires_quality_cli``. Die Schematests laufen sofort, weil sie nur die
Contract-Artefakte prüfen.
"""
from __future__ import annotations

import json
import shlex
from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape

import pytest
import yaml
from click.testing import CliRunner, Result
from jsonschema import Draft202012Validator

REPO = Path(__file__).resolve().parents[2]
_DATA = REPO / ".sdd" / "contracts" / "data"

SCHEMAS = {
    "quality_config": _DATA / "quality-config-sonden-normierung-und-suppressions-in-sdd-quality-yaml.schema.json",
    "exchange": _DATA / "austauschformate-sdd-deps-sdd-metrics-und-sdd-findings.schema.json",
    "architecture": _DATA / "architekturregeln-und-baseline.schema.json",
    "report": _DATA / "quality-report.schema.json",
    "baseline": _DATA / "architektur-baseline.schema.json",
}


def schema_validator(name: str) -> Draft202012Validator:
    schema = json.loads(SCHEMAS[name].read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def schema_errors(name: str, instance: object) -> list[str]:
    return [e.message for e in schema_validator(name).iter_errors(instance)]


def _cli_hat_quality() -> bool:
    from sdd_cli.main import cli

    return "quality" in cli.commands and "arch" in cli.commands


requires_quality_cli = pytest.mark.skipif(
    not _cli_hat_quality(), reason="sdd quality/arch noch nicht implementiert (SPEC-0054)"
)


# ── Austauschformate als Text ─────────────────────────────────────────────────

def junit(cases: list[tuple[str, str, list[str]]]) -> str:
    """JUnit-XML. cases: (name, status, fr_ids) mit status passed|failed|error|skipped."""
    zeilen = ['<?xml version="1.0" encoding="utf-8"?>', "<testsuites>",
              f'<testsuite name="probe" tests="{len(cases)}">']
    for name, status, frs in cases:
        zeilen.append(f'<testcase classname="t" name="{escape(name)}">')
        if frs:
            zeilen.append("<properties>" + "".join(
                f'<property name="fr" value="{fr}"/>' for fr in frs) + "</properties>")
        if status == "failed":
            zeilen.append('<failure message="assert">assert False</failure>')
        elif status == "error":
            zeilen.append('<error message="boom">Traceback</error>')
        elif status == "skipped":
            zeilen.append('<skipped message="skip"/>')
        zeilen.append("</testcase>")
    zeilen += ["</testsuite>", "</testsuites>"]
    return "\n".join(zeilen) + "\n"


def sarif(results: list[dict]) -> str:
    """SARIF 2.1.0 mit einem Run. results: dicts mit rule, file, line und optional level."""
    res = []
    for r in results:
        eintrag = {
            "ruleId": r["rule"],
            "message": {"text": r.get("message", r["rule"])},
            "locations": [{"physicalLocation": {
                "artifactLocation": {"uri": r["file"]},
                "region": {"startLine": r["line"]},
            }}],
        }
        if "level" in r:
            eintrag["level"] = r["level"]
        res.append(eintrag)
    return json.dumps({"version": "2.1.0", "runs": [{"tool": {"driver": {"name": "fake"}},
                                                      "results": res}]})


def deps(edges: list[dict], kinds: tuple[str, ...] = ("import",)) -> str:
    voll = []
    for e in edges:
        kante = {"to": None, "kind": "import", "line": 1, **e}
        kante.setdefault("file", kante["from"])
        kante.setdefault("symbol", Path(str(kante["to"] or "x")).stem)
        if kante["to"] is None:
            kante["unresolved"] = True
        voll.append(kante)
    return json.dumps({"format": "sdd-deps", "version": 1, "kinds_provided": list(kinds),
                       "edges": voll})


def metrics(werte: dict[str, float]) -> str:
    return json.dumps({"format": "sdd-metrics", "version": 1,
                       "metrics": [{"name": k, "value": v} for k, v in werte.items()]})


def findings(eintraege: list[dict]) -> str:
    voll = [{"message": e["rule"], "severity": "warning", **e} for e in eintraege]
    return json.dumps({"format": "sdd-findings", "version": 1, "findings": voll})


# ── Projekt ───────────────────────────────────────────────────────────────────

SPEC_ID = "SPEC-0900"


@dataclass
class QualityProject:
    root: Path
    monkeypatch: pytest.MonkeyPatch

    # Dateien
    def write(self, rel: str, text: str) -> Path:
        pfad = self.root / rel
        pfad.parent.mkdir(parents=True, exist_ok=True)
        pfad.write_text(text, encoding="utf-8")
        return pfad

    def source(self, rel: str, lines: int) -> Path:
        """Quelldatei mit genau `lines` Zeilen (Basis für Kennzahlen je 1000 Zeilen)."""
        return self.write(rel, "".join(f"x{i} = {i}\n" for i in range(lines)))

    # Sonden
    def fixture_probe(self, name: str, content: str, fmt: str, **extra: object) -> dict:
        """Sonde, die `content` unverändert nach {out} kopiert."""
        datei = self.write(f".fixtures/{name}.out", content)
        return {"command": f"cp {shlex.quote(str(datei))} {{out}}", "format": fmt, **extra}

    def quality_yaml(self, probes: dict, **extra: object) -> None:
        self.write(".sdd/quality.yaml",
                   yaml.safe_dump({"version": 1, "probes": probes, **extra}, sort_keys=False))

    def config_quality(self, quality: dict) -> None:
        pfad = self.root / ".sdd" / "config.yaml"
        daten = yaml.safe_load(pfad.read_text(encoding="utf-8")) or {}
        daten["quality"] = quality
        pfad.write_text(yaml.safe_dump(daten, sort_keys=False), encoding="utf-8")

    def architecture(self, layers: dict, rules: list[dict]) -> None:
        self.write(".sdd/architecture.yaml",
                   yaml.safe_dump({"version": 1, "layers": layers, "rules": rules},
                                  sort_keys=False))

    def adr(self, adr_id: str, title: str, status: str = "accepted",
            enforced_by: tuple[str, ...] = ()) -> None:
        nr = adr_id.split("-")[1]
        self.write(
            f"docs/adr/{adr_id}-adr-{nr}.md",
            "---\n" + yaml.safe_dump({
                "id": adr_id, "title": title, "status": status, "date": "2026-09-25",
                "deciders": ["Test"], "related_specs": [], "supersedes": "",
                "enforced_by": list(enforced_by),
            }, sort_keys=False, allow_unicode=True) + f"---\n\n# {adr_id}: {title}\n",
        )

    def spec(self, frs: list[str], fr_test_map: dict | None = None,
             contracts: tuple[str, ...] = ()) -> None:
        fm = {"id": SPEC_ID, "title": "Testspec", "type": "feature", "status": "approved",
              "owner": "Test", "created": "2026-09-25", "updated": "2026-09-25",
              "version": "0.1.0", "priority": "low", "contracts": list(contracts), "tests": []}
        if fr_test_map:
            fm["fr_test_map"] = fr_test_map
        body = "\n".join(f"- **{fr}:** Anforderung {fr}." for fr in frs)
        self.write(f".sdd/specs/{SPEC_ID}-testspec.md",
                   "---\n" + yaml.safe_dump(fm, sort_keys=False) + "---\n\n# Testspec\n\n"
                   "## 4. Funktionale Anforderungen\n\n" + body + "\n")

    def evaluation(self, name: str, scenarios: list[tuple[str, bool]],
                   verdicts: list[str] | None = None) -> None:
        """Evaluator-Ergebnis im Format von evaluator.EvaluationReport.to_dict.

        verdicts: je Szenario optional das llm_verdict seines einzigen Laufs
        (z. B. "skip" oder "error"); ohne Angabe gibt es keine Läufe.
        """
        passed = sum(1 for _, ok in scenarios if ok)
        verdicts = verdicts or [""] * len(scenarios)
        self.write(f".sdd/evaluations/{name}.json", json.dumps({
            "timestamp": name, "base_url": "http://localhost",
            "summary": {"total": len(scenarios), "passed": passed,
                        "failed": len(scenarios) - passed,
                        "pass_rate": passed / len(scenarios)},
            "scenarios": [{"hol_id": f"HOL-{i:04d}", "title": f"s{i}", "contract": con,
                           "passed": ok, "pass_count": 1 if ok else 0, "priority": "normal",
                           "runs": [{"llm_verdict": v}] if v else []}
                          for i, ((con, ok), v) in enumerate(zip(scenarios, verdicts, strict=True), 1)],
        }))

    # Aufrufe
    def run(self, *args: str) -> Result:
        from sdd_cli.main import cli

        self.monkeypatch.chdir(self.root)
        return CliRunner().invoke(cli, list(args))

    def measure(self, *args: str) -> tuple[Result, dict]:
        ergebnis = self.run("quality", "measure", "--json", *args)
        assert ergebnis.exit_code in (0, 1), ergebnis.output + ergebnis.stderr
        return ergebnis, json.loads(ergebnis.stdout)


def make_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> QualityProject:
    from sdd_cli.init import init_project

    init_project(tmp_path, title="Qualitaetsprojekt")
    return QualityProject(tmp_path, monkeypatch)


# ── Report-Zugriff ────────────────────────────────────────────────────────────

def node(report: dict, path: str) -> dict:
    """Knoten per Punktpfad, z. B. "code_quality" oder "code_quality.lint_per_kloc"."""
    teile = path.split(".")
    aktuell = report["tree"]
    for i, teil in enumerate(teile):
        kinder = {k["name"]: k for k in aktuell.get("children", [])}
        if teil in kinder:
            aktuell = kinder[teil]
            continue
        metriken = {m["name"]: m for m in aktuell.get("metrics", [])}
        if i == len(teile) - 1 and teil in metriken:
            return metriken[teil]
        raise KeyError(path)
    return aktuell


def score(report: dict, path: str) -> float | None:
    eintrag = node(report, path)
    return eintrag["score"] if "score" in eintrag else eintrag["normalized"]


def fr_status(report: dict) -> dict[str, str]:
    return {fr["id"]: fr["status"] for fr in report["requirements"]["frs"]}


def standard_projekt(p: QualityProject, *, frs: list[str] | None = None,
                     tests: list[tuple[str, str, list[str]]] | None = None,
                     metrik: dict[str, float] | None = None,
                     normalization: dict | None = None,
                     rules: int = 0) -> None:
    """Projekt mit Testsonde, Metriksonde und Abhängigkeitssonde; alles grün, wenn nicht anders gesetzt."""
    frs = frs or ["FR-01"]
    p.spec(frs)
    p.source("src/app.py", 100)
    tests = tests if tests is not None else [(f"test_{fr}", "passed", [fr]) for fr in frs]
    metrik = metrik or {"m": 0.0}
    probes = {
        "tests": p.fixture_probe("tests", junit(tests), "junit", role="tests",
                                 fr_marker="property"),
        "metriken": p.fixture_probe("metriken", metrics(metrik), "sdd-metrics"),
        "imports": p.fixture_probe("imports", deps([]), "sdd-deps", role="deps"),
    }
    p.quality_yaml(probes, paths=["src/**"],
                   normalization=normalization or {k: {"good": 0, "bad": 10} for k in metrik})
    p.architecture({"src": ["src/**"]},
                   [{"id": f"ARCH-{i:02d}", "adr": "ADR-0101", "kind": "forbidden_dependency",
                     "from": "src", "to_paths": [f"verboten{i}/**"]} for i in range(1, rules + 1)]
                   or [{"id": "ARCH-01", "adr": "ADR-0101", "kind": "forbidden_dependency",
                        "from": "src", "to_paths": ["verboten/**"]}])
    p.adr("ADR-0101", "Testentscheidung")
