"""Auto Test Generator – CON-0028, SPEC-0014."""
from __future__ import annotations

import ast
import re
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class GenerationResult:
    generated_files: list[dict] = field(default_factory=list)
    success: bool = True
    syntax_errors: list[str] = field(default_factory=list)


_SLUGIFY_RE = re.compile(r"[^a-z0-9]+")

# Platzhalter, wie ihn `sdd new test` in artifact: schreibt – kein echter Pfad.
_PLACEHOLDER_SEGMENT = "<level>"

# Output-Pfade pro Contract-Format laut CON-0028 ("Generierungsstrategie pro
# Format"). Greift nur, wenn kein TST-Dokument den Zielpfad deklariert.
_FORMAT_DIR = {
    "gherkin":     "behavior",
    "markdown":    "behavior",
    "openapi":     "api",
    "json-schema": "data",
    "slo-yaml":    "performance",
}


def _slug(text: str) -> str:
    return _SLUGIFY_RE.sub("_", text.lower()).strip("_")[:50]


def _zeigt_nach_sdd(pfad: str) -> bool:
    """Liegt der Pfad unterhalb von .sdd/?

    CON-0028: "Der ausfuehrbare Testcode liegt in allen drei Faellen unter
    tests/; .sdd/ haelt ausschliesslich die SDD-Dokumente." Der Generator nahm
    bisher jeden Pfad, den ein TST-Dokument nannte. Vier Dokumente zeigten nach
    .sdd/tests/ — 27 Tests lagen dort und liefen nie mit (#94).
    """
    teile = Path(pfad).parts
    return bool(teile) and teile[0] == ".sdd"


def _extract_scenarios(feature_text: str) -> list[str]:
    """Extract scenario titles from a .feature file."""
    titles = []
    for line in feature_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("Scenario:") or stripped.startswith("Scenario Outline:"):
            title = stripped.split(":", 1)[1].strip()
            titles.append(title)
    return titles


def _extract_manual_functions(existing: str, generated: str) -> str:
    """Return function bodies present in `existing` but not in `generated`."""
    def _func_names(src: str) -> set[str]:
        names = set()
        for line in src.splitlines():
            m = re.match(r"^def (test_\w+)\(", line)
            if m:
                names.add(m.group(1))
        return names

    gen_names = _func_names(generated)
    ex_names = _func_names(existing)
    manual_names = ex_names - gen_names
    if not manual_names:
        return ""

    # Extract each manual function body
    blocks = []
    lines = existing.splitlines(keepends=True)
    i = 0
    while i < len(lines):
        m = re.match(r"^def (test_\w+)\(", lines[i])
        if m and m.group(1) in manual_names:
            block = [lines[i]]
            i += 1
            while i < len(lines) and (lines[i].startswith(" ") or lines[i].strip() == ""):
                block.append(lines[i])
                i += 1
            blocks.append("".join(block).rstrip())
        else:
            i += 1
    return "\n\n".join(blocks)


class TestGenerator:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = Path(repo_root)

    # ── Contract finding ──────────────────────────────────────────────────────

    def _find_contract(self, con_id: str) -> dict | None:
        contracts_dir = self.repo_root / ".sdd" / "contracts"
        if not contracts_dir.exists():
            return None
        import yaml, re as _re
        for md in sorted(contracts_dir.rglob("*.md")):
            try:
                content = md.read_text(encoding="utf-8")
                m = _re.match(r"^---\n(.*?)\n---\n?(.*)", content, _re.DOTALL)
                if m:
                    fm = yaml.safe_load(m.group(1)) or {}
                    if fm.get("id") == con_id:
                        fm["_body"] = m.group(2)
                        fm["_path"] = str(md)
                        return fm
            except Exception:
                pass
        return None

    def _read_artifact(self, contract: dict) -> str:
        artifact = contract.get("artifact", "")
        if not artifact:
            return ""
        p = self.repo_root / artifact
        if p.exists():
            return p.read_text(encoding="utf-8")
        return ""

    # ── Template rendering ────────────────────────────────────────────────────

    def _render_template(self, contract: dict) -> str:
        """Generate Python test file content for a contract."""
        con_id = contract.get("id", "CON-XXXX")
        title = contract.get("title", "")
        spec = contract.get("spec", "")
        fmt = contract.get("format", "markdown")
        con_id_lower = con_id.lower()

        header = (
            f"# AUTO-GENERATED from {con_id} via sdd test generate — do not delete\n"
            f'"""Contract-Tests für {title} ({con_id}).\n\n'
            f"Spec: {spec} · Contract: {con_id}\n"
            '"""\n'
            "from __future__ import annotations\n\n"
            "import pytest\n"
        )

        if fmt == "gherkin":
            artifact_text = self._read_artifact(contract)
            scenarios = _extract_scenarios(artifact_text) if artifact_text else []
            if not scenarios:
                # Fallback: try to extract from body
                scenarios = _extract_scenarios(contract.get("_body", ""))
            functions = []
            for i, title_s in enumerate(scenarios, 1):
                fn = f"test_tc{i:02d}_{_slug(title_s)}"
                error_hint = "error" in title_s.lower() or "fehler" in title_s.lower()
                body = (
                    f'    """Scenario: {title_s} ({con_id})."""\n'
                )
                if error_hint:
                    body += (
                        "    # TODO: verify error/rejection behaviour\n"
                        "    pytest.skip(\"Test noch nicht implementiert\")\n"
                    )
                else:
                    body += "    pytest.skip(\"Test noch nicht implementiert\")\n"
                functions.append(f"\ndef {fn}():\n{body}")
            return header + "".join(functions) + "\n"

        if fmt == "openapi":
            artifact_text = self._read_artifact(contract)
            # Extract paths from OpenAPI yaml
            paths: list[str] = []
            try:
                import yaml
                spec_data = yaml.safe_load(artifact_text) or {}
                paths = list((spec_data.get("paths") or {}).keys())
            except Exception:
                pass
            functions = []
            for i, path in enumerate(paths or ["<endpoint>"], 1):
                fn = f"test_tc{i:02d}_{_slug(path)}"
                functions.append(
                    f"\ndef {fn}():\n"
                    f'    """Happy-path für {path} ({con_id})."""\n'
                    "    import httpx\n"
                    "    # TODO: configure base_url and assert response\n"
                    "    pytest.skip(\"Test noch nicht implementiert\")\n"
                )
            if not functions:
                functions = [
                    "\ndef test_tc01_endpoint():\n"
                    '    """API contract test ({con_id})."""\n'
                    "    import httpx\n"
                    "    pytest.skip(\"Test noch nicht implementiert\")\n"
                ]
            return header + "".join(functions) + "\n"

        if fmt == "json-schema":
            return (
                header
                + "\nimport json\nimport jsonschema\n"
                + f"\n\ndef test_tc01_valid_instance_passes():\n"
                f'    """Valide Instanz besteht Schema-Validierung ({con_id})."""\n'
                "    pytest.skip(\"Test noch nicht implementiert\")\n"
                f"\n\ndef test_tc02_invalid_instance_rejected():\n"
                f'    """Invalide Instanz wird abgelehnt ({con_id})."""\n'
                "    pytest.skip(\"Test noch nicht implementiert\")\n\n"
            )

        # fallback / markdown
        return (
            header
            + f"\n\ndef test_tc01_{_slug(con_id)}():\n"
            f'    """Contract test ({con_id})."""\n'
            "    pytest.skip(\"Test noch nicht implementiert\")\n\n"
        )

    # ── Zielpfad aus dem Test-Dokument ────────────────────────────────────────
    #
    # Der Pfad war fest verdrahtet (.sdd/tests/contract/test_<con>.py). Damit
    # entstand die unter `artifact:` deklarierte Datei nie, und der erzeugten
    # Datei war kein Test-Dokument zugeordnet — die Traceability riss genau
    # dort, wo sie in Code uebergehen soll.

    def _find_test_doc(self, con_id: str) -> dict | None:
        """Sucht das TST-Dokument, dessen contract:-Feld auf con_id zeigt."""
        import re as _re

        import yaml

        for base in (self.repo_root / ".sdd" / "tests", self.repo_root / "tests"):
            if not base.exists():
                continue
            for md in sorted(base.rglob("*.md")):
                try:
                    m = _re.match(r"^---\n(.*?)\n---\n?(.*)",
                                  md.read_text(encoding="utf-8"), _re.DOTALL)
                except OSError:
                    continue
                if not m:
                    continue
                fm = yaml.safe_load(m.group(1)) or {}
                if not isinstance(fm, dict):
                    continue
                if str(fm.get("id", "")).startswith("TST-") and fm.get("contract") == con_id:
                    return fm
        return None

    def _output_path(self, con_id: str, contract: dict) -> Path:
        """Zielpfad fuer den generierten Testcode, in dieser Rangfolge:

        1. `artifact:` des zugehoerigen TST-Dokuments — die deklarierte Datei.
        2. `tests/<level>/` mit dem `level:` des Dokuments, falls kein artifact.
        3. Die Format-Tabelle aus CON-0028, falls gar kein TST-Dokument da ist.

        Der ausfuehrbare Testcode gehoert nach tests/; .sdd/ haelt die
        SDD-Dokumente. Der fest verdrahtete Pfad .sdd/tests/contract/ verletzte
        beides zugleich.
        """
        doc = self._find_test_doc(con_id) or {}

        artifact = str(doc.get("artifact") or "").strip().strip('"')
        if artifact and _PLACEHOLDER_SEGMENT not in artifact and not _zeigt_nach_sdd(artifact):
            return self.repo_root / artifact

        if doc.get("level"):
            return self.repo_root / "tests" / str(doc["level"]).strip() / f"test_{con_id.lower()}.py"

        fmt = str(contract.get("format") or "").strip()
        return self.repo_root / "tests" / _FORMAT_DIR.get(fmt, "contract") / f"test_{con_id.lower()}.py"

    # ── File writing with manual-addition preservation ────────────────────────

    def _write_with_preservation(self, out_path: Path, new_content: str) -> None:
        if out_path.exists():
            existing = out_path.read_text(encoding="utf-8")
            manual = _extract_manual_functions(existing, new_content)
            if manual:
                new_content = new_content.rstrip() + "\n\n\n" + manual + "\n"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(new_content, encoding="utf-8")

    # ── Main entry point ──────────────────────────────────────────────────────

    def generate(self, spec_id: str, contracts: list[str]) -> GenerationResult:
        result = GenerationResult()
        for con_id in contracts:
            contract = self._find_contract(con_id)
            if contract is None:
                continue

            out_path = self._output_path(con_id, contract)

            try:
                content = self._render_template(contract)
            except Exception as exc:
                result.success = False
                result.syntax_errors.append(f"{con_id}: render error: {exc}")
                continue

            # Syntax check
            try:
                ast.parse(content)
            except SyntaxError as exc:
                result.success = False
                result.syntax_errors.append(f"{out_path.name}:{exc.lineno}: {exc.msg}")
                # Still write so caller can inspect; also triggers TC-06
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_text(content, encoding="utf-8")
                continue

            self._write_with_preservation(out_path, content)

            test_count = sum(
                1 for line in content.splitlines() if line.startswith("def test_")
            )
            result.generated_files.append({
                "contract_id": con_id,
                "path": str(out_path.relative_to(self.repo_root)),
                "test_count": test_count,
            })

        return result
