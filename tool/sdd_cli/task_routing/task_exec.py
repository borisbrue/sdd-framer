"""ImplOnlyExecutor – lokales LLM implementiert Code für vorhandene Test-Datei.

Setzt voraus, dass die Test-Datei bereits existiert und rot ist (RED-Phase durch
Claude abgeschlossen). Der Executor übernimmt nur die Implementierungsphase.

Pattern: Strategy (austauschbare Implementierungsstrategie im TDD-Loop)
"""
from __future__ import annotations

import re
import shlex
import subprocess
from pathlib import Path
from typing import Any


class ImplOnlyExecutor:
    """Führt den Implementierungsschritt für einen Task via lokalem LLM aus.

    Ablauf: Test lesen → Modulpfade ableiten → Prompt bauen →
    LLM aufrufen → Code auf Disk schreiben → pytest ausführen.
    """

    def __init__(self, config: Any, project_root: Path) -> None:
        self._config = config
        self._project_root = project_root

    def execute(
        self,
        task: Any,
        test_file: Path,
        iteration: int = 1,
        error_context: str = "",
    ) -> tuple[bool, str]:
        """Implementiert einen Task via lokalem LLM.

        Args:
            task: Task-Objekt oder dict mit description + test_command.
            test_file: Pfad zur bereits vorhandenen roten Test-Datei.
            iteration: Versuchs-Nummer (≥2 = Retry mit Fehlerkontext).
            error_context: pytest-Ausgabe des vorherigen fehlgeschlagenen Versuchs.

        Returns:
            (success, pytest_output)
        """
        from ..llm import get_completion_provider

        provider = get_completion_provider(self._config, "local_llm")
        test_content = test_file.read_text()
        write_targets, context_files = self._extract_impl_targets(test_content)

        if not write_targets:
            raise ValueError(
                f"Keine fehlenden 'from sdd_cli.*'- oder 'from tool.sdd_cli.*'-Importe "
                f"in {test_file} gefunden. "
                "Alle importierten Module existieren bereits — nichts zu implementieren."
            )

        for module, impl_file in write_targets:
            prompt = self._build_prompt(
                task, test_content, impl_file,
                context_files=context_files,
                iteration=iteration,
                error_context=error_context,
            )
            result = provider.complete(prompt, max_tokens=6144)
            code = _strip_code_block(result.text)
            impl_file.parent.mkdir(parents=True, exist_ok=True)
            impl_file.write_text(code)

        cmd = (
            task.get("test_command") if isinstance(task, dict) else getattr(task, "test_command", None)
        ) or f"pytest {test_file} -x --tb=short"
        return _run_tests(cmd, self._project_root)

    def _extract_impl_targets(
        self, test_content: str
    ) -> tuple[list[tuple[str, Path]], list[tuple[str, Path]]]:
        """Trennt Imports in Write-Targets (fehlen noch) und Kontext-Dateien (existieren).

        Returns:
            (write_targets, context_files) — nur write_targets werden beschrieben.
        """
        seen: set[str] = set()
        write_targets: list[tuple[str, Path]] = []
        context_files: list[tuple[str, Path]] = []
        for m in re.finditer(
            r"from ((?:tool\.)?sdd_cli\.[^\s]+) import", test_content
        ):
            module = m.group(1)
            if module not in seen:
                seen.add(module)
                path = self._module_to_path(module)
                if path.exists():
                    context_files.append((module, path))
                else:
                    write_targets.append((module, path))
        return write_targets, context_files

    def _module_to_path(self, module: str) -> Path:
        # Normalize: sdd_cli.foo → tool/sdd_cli/foo.py
        #            tool.sdd_cli.foo → tool/sdd_cli/foo.py
        parts = module.split(".")
        if parts[0] != "tool":
            parts = ["tool"] + parts
        return self._project_root.joinpath(*parts).with_suffix(".py")

    def _build_prompt(
        self,
        task: Any,
        test_content: str,
        impl_file: Path,
        context_files: list[tuple[str, Path]] | None = None,
        iteration: int = 1,
        error_context: str = "",
    ) -> str:
        if isinstance(task, dict):
            desc = task.get("description", task.get("title", ""))
        else:
            desc = getattr(task, "description", str(task))

        rel = impl_file.relative_to(self._project_root) if impl_file.is_absolute() else impl_file

        lines = [
            f"Schreibe den vollständigen Inhalt der Datei `{rel}`.",
            f"Aufgabe: {desc}",
            "",
        ]

        if context_files:
            lines.append("## API vorhandener Module (NUR Kontext – nicht implementieren)")
            for _module, ctx_path in context_files:
                ctx_rel = ctx_path.relative_to(self._project_root) if ctx_path.is_absolute() else ctx_path
                api_summary = _extract_class_api(ctx_path.read_text())
                lines += [
                    f"### {ctx_rel}",
                    "```python",
                    api_summary,
                    "```",
                    "",
                ]

        lines += [
            "## Test-Datei (bereits vorhanden – muss nach deiner Implementierung grün sein)",
            "```python",
            test_content,
            "```",
        ]

        if iteration > 1 and error_context:
            lines += [
                "",
                f"## Fehler aus Versuch {iteration - 1}",
                "```",
                error_context,
                "```",
                "Analysiere den Fehler und korrigiere die Implementierung.",
            ]

        skeleton = _build_skeleton(test_content, impl_file, context_files or [])
        if skeleton:
            lines += [
                "",
                "## Code-Skelett (vervollständige die TODO-Stellen)",
                "```python",
                skeleton,
                "```",
            ]

        lines += [
            "",
            "## Ausgabe-Regeln",
            f"- Schreibe NUR den vollständigen Inhalt für `{rel}`",
            "- Ersetze alle TODO-Kommentare durch echte Implementierung",
            "- Kein Markdown-Wrapper (kein ```python ... ```)",
            "- Keine Erklärungen, kein Fließtext",
            "- Keine Test-Klassen, keine Beispiel-Strings aus dem Test",
            "- Valider Python-Code ab der ersten Zeile",
        ]
        return "\n".join(lines)


def decide_routing(task_dict: dict, routing_config: Any) -> str:
    """Gibt 'local' oder 'claude' zurück für einen Task-Dict.

    Nutzt den complexity-Wert des Tasks als Proxy für complexity_score,
    da Task-JSONs aus .sdd/tasks/ keine computed score-Felder haben.
    """
    from .config import TaskRoutingConfig
    from .router import decide_executor

    if not isinstance(routing_config, TaskRoutingConfig):
        raise TypeError("routing_config muss TaskRoutingConfig sein")

    # Complexity-Text → approximate score
    _SCORE_MAP = {"low": 15, "medium": 50, "high": 80}
    complexity = task_dict.get("complexity", "medium")
    score = _SCORE_MAP.get(complexity, 50)

    class _Proxy:
        complexity_score = score

    return decide_executor(_Proxy(), routing_config)


def _extract_class_api(source: str) -> str:
    """Extrahiert Klassen-Signaturen und Attribute aus Python-Quellcode.

    Gibt eine kompakte Übersicht zurück: Klassenname, Felder (dataclass),
    Methoden-Signaturen — ohne Implementierungsdetails.
    """
    result: list[str] = []
    current_class: str | None = None
    in_body = False

    for line in source.splitlines():
        stripped = line.strip()

        # Klassen-Deklaration
        if stripped.startswith("class ") and ":" in stripped:
            current_class = stripped
            result.append(stripped)
            in_body = True
            continue

        if not in_body:
            # Top-Level imports
            if stripped.startswith(("from ", "import ", "@dataclass")):
                result.append(stripped)
            continue

        # Innerhalb einer Klasse
        if stripped.startswith("def ") or stripped.startswith("async def "):
            # Nur Signatur, kein Body
            sig = stripped.split("->")[0].rstrip() + (" -> ..." if "->" in stripped else "")
            result.append("    " + sig)
        elif stripped.startswith("@"):
            result.append("    " + stripped)
        elif ":" in stripped and not stripped.startswith("#") and not stripped.startswith('"'):
            # Dataclass-Felder oder Typ-Annotierungen
            if not stripped.startswith("if ") and not stripped.startswith("for "):
                result.append("    " + stripped)
        elif stripped == "" and current_class:
            result.append("")

    return "\n".join(result)


def _build_skeleton(
    test_content: str,
    impl_file: Path,
    context_files: list[tuple[str, Path]],
) -> str:
    """Generiert ein ausfüllbares Code-Skelett für die Zieldatei."""
    # Zieldatei → Modul-IDs in beiden Varianten:
    #   tool/sdd_cli/vision/stats.py → tool.sdd_cli.vision.stats  UND  sdd_cli.vision.stats
    parts = impl_file.with_suffix("").parts
    try:
        tool_module = ".".join(parts[parts.index("tool"):])
    except ValueError:
        return ""
    short_module = ".".join(parts[parts.index("sdd_cli"):]) if "sdd_cli" in parts else tool_module

    # Klassen die aus der ZIELDATEI importiert werden – beide Import-Varianten prüfen
    cls_names: list[str] = list(dict.fromkeys(
        m.group(1)
        for pattern in (tool_module, short_module)
        for m in re.finditer(
            rf"from {re.escape(pattern)} import (\w+)", test_content
        )
    ))
    if not cls_names:
        return ""

    header: list[str] = ["from __future__ import annotations", "from dataclasses import dataclass"]

    # Kontext-Importe
    for module, _ in context_files:
        names = list(dict.fromkeys(
            m.group(1)
            for m in re.finditer(rf"from {re.escape(module)} import (\w+)", test_content)
        ))
        if names:
            header.append(f"from .{module.split('.')[-1]} import {', '.join(names)}")

    header.append("")

    is_frozen = bool(re.search(
        r"frozen=True|FrozenInstanceError|pytest\.raises\([^)]*(?:AttributeError|TypeError)", test_content
    ))
    decorator = "@dataclass(frozen=True)" if is_frozen else "@dataclass"

    body: list[str] = []
    for cls_name in cls_names:
        # Instanzattribute: `stats.fieldname`, `result.fieldname` etc.
        fields: list[str] = list(dict.fromkeys(
            m.group(1)
            for m in re.finditer(r"\bstats\.([a-z][a-z_0-9]+)\b", test_content)
        ))

        body += [decorator, f"class {cls_name}:"]
        body += [f"    {f}: int" for f in fields] or ["    pass"]
        body.append("")

        # Klassenmethoden: `ClassName.method(arg)` → @classmethod
        seen: set[str] = set()
        for cm in re.finditer(rf"{re.escape(cls_name)}\.([a-z_]+)\(([^)]*)\)", test_content):
            mname, args = cm.group(1), cm.group(2).strip()
            if mname in seen:
                continue
            seen.add(mname)
            body += [
                "    @classmethod",
                f"    def {mname}(cls, {args}) -> \"{cls_name}\":",
                f"        # TODO: {args} auswerten, alle Felder berechnen",
                "        return cls(",
                "            # TODO: Felder mit berechneten Werten",
                "        )",
                "",
            ]

    return "\n".join(header + body)


def _extract_api_signatures(test_content: str) -> str:
    """Leitet aus dem Test-Code konkrete API-Signaturen ab.

    Erkennt Muster wie:
      ClassName.classmethod(args)    → @classmethod def classmethod(cls, args)
      instance.method(args)          → def method(self, args)
      ClassName(field=value, ...)    → __init__ / dataclass-Felder
    """
    lines: list[str] = []
    seen_classes: set[str] = set()

    # Klassen die in der Zieldatei importiert werden (aus dem Import-Pattern)
    for m in re.finditer(
        r"from (?:tool\.)?sdd_cli\.[^\s]+ import ([A-Z][A-Za-z0-9_]+)", test_content
    ):
        cls_name = m.group(1)
        if cls_name in seen_classes:
            continue
        seen_classes.add(cls_name)

        # Classmethod-Aufrufe: ClassName.method(...)
        for cm in re.finditer(
            rf"{re.escape(cls_name)}\.([a-z_]+)\(([^)]*)\)", test_content
        ):
            lines.append(
                f"{cls_name}.{cm.group(1)}({cm.group(2).strip()})  # classmethod"
            )

        # Instanzattribute-Zugriffe: instance.field
        attrs: set[str] = set()
        for am in re.finditer(rf"\bstats\.([a-z_]+)\b", test_content):
            attrs.add(am.group(1))
        if attrs:
            lines.append(f"{cls_name} hat Attribute: {', '.join(sorted(attrs))}")

        # Frozen-Check: `with pytest.raises((AttributeError, TypeError)): stats.X = …`
        if re.search(r"pytest\.raises.*AttributeError.*FrozenInstanceError|frozen", test_content):
            lines.append(f"{cls_name} muss als frozen=True Dataclass implementiert werden")

    return "\n".join(lines)


def _strip_code_block(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        inner = lines[1:]
        if inner and inner[-1].strip() == "```":
            inner = inner[:-1]
        text = "\n".join(inner)
    return text


def _run_tests(test_command: str, cwd: Path) -> tuple[bool, str]:
    import shutil

    # pytest nicht im PATH (z.B. uv-Tool-Kontext) → via uv run
    parts = shlex.split(test_command)
    if parts and parts[0] == "pytest" and not shutil.which("pytest"):
        uv = shutil.which("uv")
        if uv:
            parts = [uv, "run"] + parts
    try:
        result = subprocess.run(
            parts,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=120,
        )
        output = result.stdout + result.stderr
        return result.returncode == 0, output
    except subprocess.TimeoutExpired:
        return False, "TIMEOUT: Test-Command überschritt 120 Sekunden."
