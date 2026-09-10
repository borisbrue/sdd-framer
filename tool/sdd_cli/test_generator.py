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


@dataclass
class WriteOutcome:
    """Was mit der Zieldatei tatsaechlich geschah.

    Vorher meldete jeder Lauf pauschal Erfolg mit der Testzahl der *Vorlage*.
    Eine Datei mit 27 Tests, die auf 22 Stubs zusammengestrichen wurde, kam als
    "(22 Tests)" durch — das einzige Warnsignal war eine Zahl, die niemand mit
    dem Dateiinhalt verglich.
    """

    status: str            # created | extended | unchanged | overwritten | unparsable
    test_count: int = 0    # Tests in der Datei DANACH, nicht in der Vorlage
    stubs_added: int = 0
    backup: Path | None = None


_SLUGIFY_RE = re.compile(r"[^a-z0-9]+")

# Platzhalter, wie ihn `sdd new test` in artifact: schreibt – kein echter Pfad.
_PLACEHOLDER_SEGMENT = "<level>"

# Output-Pfade pro Contract-Format laut CON-0028 ("Generierungsstrategie pro
# Format"). Greift nur, wenn kein TST-Dokument den Zielpfad deklariert.
_FORMAT_DIR = {
    "gherkin":     "behavior",
    "markdown":    "behavior",
    "openapi":     "api",
    "asyncapi":    "api",
    "json-schema": "data",
    "slo-yaml":    "performance",
}


# Umlaute und ss wurden von _SLUGIFY_RE verworfen: "Oberfläche" ergab
# "oberfl_che". Transliteration erhaelt den Namen, statt ihn zu zerloechern.
_TRANSLITERATION = str.maketrans({
    "ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss",
    "Ä": "ae", "Ö": "oe", "Ü": "ue",
    "á": "a", "à": "a", "â": "a", "é": "e", "è": "e", "ê": "e",
    "í": "i", "ì": "i", "î": "i", "ó": "o", "ò": "o", "ô": "o",
    "ú": "u", "ù": "u", "û": "u", "ç": "c", "ñ": "n",
})


def _slug(text: str, fallback: str = "root") -> str:
    """Bezeichnerfreundlicher Name. Nie leer.

    Fuer den Pfad "/" entstand vorher ein leerer Namensteil und damit
    `def test_tc01_():` — syntaktisch gueltig, aber ohne Aussage.
    """
    slug = _SLUGIFY_RE.sub("_", text.lower().translate(_TRANSLITERATION)).strip("_")[:50]
    return slug or fallback


def _module_name(con_id: str) -> str:
    """CON-0014 -> con_0014.

    Der Rueckfall bildete `test_con-0014.py` — ein Modulname mit Bindestrich
    ist nicht importierbar.
    """
    return con_id.lower().replace("-", "_")


def _zeigt_nach_sdd(pfad: str) -> bool:
    """Liegt der Pfad unterhalb von .sdd/?

    CON-0028: "Der ausfuehrbare Testcode liegt in allen drei Faellen unter
    tests/; .sdd/ haelt ausschliesslich die SDD-Dokumente." Der Generator nahm
    bisher jeden Pfad, den ein TST-Dokument nannte. Vier Dokumente zeigten nach
    .sdd/tests/ — 27 Tests lagen dort und liefen nie mit (#94).
    """
    teile = Path(pfad).parts
    return bool(teile) and teile[0] == ".sdd"


def _asyncapi_operationen(doc: dict) -> list[str]:
    """Bezeichner je Nachricht/Operation eines AsyncAPI-Dokuments.

    Der Generator zaehlte Pfade (OpenAPI) und Szenarien (Gherkin) auf,
    Nachrichten nicht — `asyncapi` fiel auf den generischen Einzelrumpf zurueck
    und meldete "(1 Tests)" fuer ein Protokoll mit drei Nachrichtenarten (#66).

    Drei Ebenen, weil AsyncAPI 2 und 3 unterschiedlich aufgebaut sind:

    - 3.x: `operations` ist die Liste der Dinge, die passieren.
    - 2.x: `channels.<name>.publish|subscribe` — je Richtung eine Operation.
    - Rueckfall: `components.messages`, wenn keins von beidem da ist.
    """
    operationen = doc.get("operations")
    if isinstance(operationen, dict) and operationen:
        return list(operationen.keys())

    kanaele = doc.get("channels")
    if isinstance(kanaele, dict) and kanaele:
        treffer: list[str] = []
        for name, kanal in kanaele.items():
            if not isinstance(kanal, dict):
                continue
            richtungen = [r for r in ("publish", "subscribe") if r in kanal]
            if richtungen:
                treffer.extend(f"{r} {name}" for r in richtungen)
            else:
                # 3.x ohne operations-Block: die Nachrichten des Kanals.
                nachrichten = kanal.get("messages")
                if isinstance(nachrichten, dict) and nachrichten:
                    treffer.extend(f"{name} {m}" for m in nachrichten)
                else:
                    treffer.append(name)
        if treffer:
            return treffer

    nachrichten = (doc.get("components") or {}).get("messages")
    if isinstance(nachrichten, dict) and nachrichten:
        return list(nachrichten.keys())
    return []


def _extract_scenarios(feature_text: str) -> list[str]:
    """Extract scenario titles from a .feature file."""
    titles = []
    for line in feature_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("Scenario:") or stripped.startswith("Scenario Outline:"):
            title = stripped.split(":", 1)[1].strip()
            titles.append(title)
    return titles


def _test_funktionen(src: str) -> dict[str, tuple[int, int]]:
    """Name -> (erste Zeile inkl. Dekoratoren, letzte Zeile), 1-basiert.

    Der Vorgaenger suchte Zeilen nach dem Muster `^def (test_\\w+)\\(` und sammelte
    danach alles ein, was mit Leerzeichen beginnt. Daraus folgte der Datenverlust
    aus #92:

    - `@pytest.mark.parametrize` steht VOR `def` und lag damit ausserhalb des
      Blocks — der Dekorator ging verloren, die Funktion behielt ihre Parameter.
    - Bei mehrzeiliger Signatur steht die schliessende `):` in Spalte 0. Die
      Sammlung brach dort ab, der Koerper fehlte, uebrig blieb ein Syntaxfehler.

    ast kennt beides: `decorator_list` gehoert zur Funktion, und wo sie endet,
    entscheidet der Parser statt der Einrueckung.
    """
    try:
        baum = ast.parse(src)
    except SyntaxError:
        return {}
    treffer: dict[str, tuple[int, int]] = {}
    for knoten in baum.body:
        if not isinstance(knoten, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not knoten.name.startswith("test_"):
            continue
        start = min([knoten.lineno] + [d.lineno for d in knoten.decorator_list])
        treffer[knoten.name] = (start, knoten.end_lineno or knoten.lineno)
    return treffer


def _block(src: str, spanne: tuple[int, int]) -> str:
    zeilen = src.splitlines()
    return "\n".join(zeilen[spanne[0] - 1 : spanne[1]]).rstrip()


def _hat_pytest_import(baum: ast.Module) -> bool:
    for knoten in ast.walk(baum):
        if isinstance(knoten, ast.Import):
            if any(a.name.split(".")[0] == "pytest" for a in knoten.names):
                return True
        elif isinstance(knoten, ast.ImportFrom):
            if (knoten.module or "").split(".")[0] == "pytest":
                return True
    return False


def _mit_pytest_import(text: str) -> str:
    """Ergaenzt `import pytest`, falls die Datei ihn nicht hat.

    Die angehaengten Ruempfe rufen `pytest.skip`. Ohne den Import waere das ein
    NameError zur Laufzeit — ein Fehler, den der Generator selbst eintraegt.
    Eingefuegt wird nach dem letzten Import auf Modulebene, sonst nach dem
    Docstring, sonst ganz oben.
    """
    try:
        baum = ast.parse(text)
    except SyntaxError:
        return text
    if _hat_pytest_import(baum):
        return text

    nach = 0
    for knoten in baum.body:
        if isinstance(knoten, (ast.Import, ast.ImportFrom)):
            nach = knoten.end_lineno or knoten.lineno
        elif (
            nach == 0
            and isinstance(knoten, ast.Expr)
            and isinstance(knoten.value, ast.Constant)
            and isinstance(knoten.value.value, str)
        ):
            nach = knoten.end_lineno or knoten.lineno
        elif nach:
            break

    zeilen = text.splitlines()
    zeilen.insert(nach, "import pytest  # von sdd test generate ergaenzt")
    return "\n".join(zeilen) + ("\n" if text.endswith("\n") else "")


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

        if fmt == "asyncapi":
            artifact_text = self._read_artifact(contract)
            operationen: list[str] = []
            try:
                import yaml
                doc = yaml.safe_load(artifact_text) or {}
                operationen = _asyncapi_operationen(doc) if isinstance(doc, dict) else []
            except Exception:
                pass

            if not operationen:
                # Ehrlich bleiben statt eine 1 zu melden: wenn sich nichts
                # aufzaehlen laesst, sagt der Rumpf warum.
                return (
                    header
                    + f"\n\ndef test_tc01_{_slug(con_id)}():\n"
                    f'    """Event-Contract {con_id} — keine Nachricht aufzaehlbar.\n\n'
                    f"    Weder operations noch channels noch components.messages im\n"
                    f"    Artifact. Ergaenze das Dokument oder schreibe die Tests von Hand.\n"
                    '    """\n'
                    "    pytest.skip(\"Test noch nicht implementiert\")\n\n"
                )

            functions = []
            for i, op in enumerate(operationen, 1):
                fn = f"test_tc{i:02d}_{_slug(op)}"
                functions.append(
                    f"\ndef {fn}():\n"
                    f'    """Nachricht/Operation {op} ({con_id})."""\n'
                    "    # TODO: Nachricht senden bzw. empfangen und Payload gegen\n"
                    "    # das Schema pruefen\n"
                    "    pytest.skip(\"Test noch nicht implementiert\")\n"
                )
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
            return (self.repo_root / "tests" / str(doc["level"]).strip()
                / f"test_{_module_name(con_id)}.py")

        fmt = str(contract.get("format") or "").strip()
        return (self.repo_root / "tests" / _FORMAT_DIR.get(fmt, "contract")
                / f"test_{_module_name(con_id)}.py")

    # ── Schreiben ohne Verlust ────────────────────────────────────────────────
    #
    # Die Richtung war verkehrt herum: gebaut wurde die Vorlage, und aus der
    # vorhandenen Datei wurden Bruchstuecke hineingerettet. Alles, was kein
    # `def test_`-Block war — Docstring, Importe, Fixtures, Konstanten,
    # Hilfsklassen — hatte in der Vorlage keinen Platz und verschwand.
    #
    # Jetzt bleibt die Datei die Grundlage. Ergaenzt wird nur, was der Contract
    # verlangt und die Datei nicht hat. CON-0028 INV-05 und INV-07 verlangen
    # genau das; erfuellt war es nicht.

    def _write_with_preservation(
        self, out_path: Path, new_content: str, force: bool = False
    ) -> WriteOutcome:
        if not out_path.exists():
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(new_content, encoding="utf-8")
            return WriteOutcome(
                "created",
                test_count=len(_test_funktionen(new_content)),
                stubs_added=len(_test_funktionen(new_content)),
            )

        existing = out_path.read_text(encoding="utf-8")

        if force:
            backup = out_path.with_suffix(out_path.suffix + ".bak")
            backup.write_text(existing, encoding="utf-8")
            out_path.write_text(new_content, encoding="utf-8")
            return WriteOutcome(
                "overwritten",
                test_count=len(_test_funktionen(new_content)),
                backup=backup,
            )

        try:
            ast.parse(existing)
        except SyntaxError:
            # Nicht auswertbar heisst nicht ueberschreibbar. Wer hier schreibt,
            # zerstoert eine Datei, die er nicht gelesen hat.
            return WriteOutcome("unparsable")

        vorhanden = _test_funktionen(existing)
        erzeugt = _test_funktionen(new_content)
        fehlend = [name for name in erzeugt if name not in vorhanden]

        if not fehlend:
            return WriteOutcome("unchanged", test_count=len(vorhanden))

        bloecke = [_block(new_content, erzeugt[name]) for name in fehlend]
        ergaenzt = _mit_pytest_import(existing).rstrip("\n")
        ergaenzt += "\n\n\n" + "\n\n\n".join(bloecke) + "\n"
        out_path.write_text(ergaenzt, encoding="utf-8")
        return WriteOutcome(
            "extended",
            test_count=len(vorhanden) + len(fehlend),
            stubs_added=len(fehlend),
        )

    # ── Main entry point ──────────────────────────────────────────────────────

    def generate(
        self, spec_id: str, contracts: list[str], force: bool = False
    ) -> GenerationResult:
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

            outcome = self._write_with_preservation(out_path, content, force=force)

            if outcome.status == "unparsable":
                result.success = False
                result.syntax_errors.append(
                    f"{out_path.relative_to(self.repo_root)}: vorhandene Datei ist "
                    f"nicht auswertbar — nicht angetastet. Repariere sie oder nutze "
                    f"--force (sichert nach .bak)."
                )

            result.generated_files.append({
                "contract_id": con_id,
                "path": str(out_path.relative_to(self.repo_root)),
                "test_count": outcome.test_count,
                "status": outcome.status,
                "stubs_added": outcome.stubs_added,
                "backup": str(outcome.backup.relative_to(self.repo_root))
                if outcome.backup else None,
            })

        return result
