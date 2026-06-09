"""Deterministischer Holdout-Runner für das strukturierte YAML-Format.

Kein LLM für Request-Planung oder Pass/Fail-Entscheidung.
LLM wird nur bei Fehlern gerufen, um aus dem Evaluation Hint einen Task-Delta
zu produzieren (einmaliger Aufruf pro fehlgeschlagenem Holdout).

Ablauf pro Holdout:
  1. Setup-Schritte ausführen, Variablen capturen
  2. Test-Action ausführen
  3. Assertions deterministisch prüfen
  4. Teardown immer ausführen (auch bei Fehler)
  5. Bei Fehler: LLM liest Evaluation Hint → Task-Delta
"""
from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


# ── YAML-Block-Extraktion ────────────────────────────────────────────────────

_BLOCK_RE = re.compile(
    r"^## (Setup|Test|Teardown|Evaluation Hint)\s*\n(.*?)(?=^## |\Z)",
    re.MULTILINE | re.DOTALL,
)
_YAML_FENCE_RE = re.compile(r"^```yaml\s*\n(.*?)^```", re.MULTILINE | re.DOTALL)


def _extract_sections(body: str) -> dict[str, str]:
    return {m.group(1): m.group(2) for m in _BLOCK_RE.finditer(body)}


def _first_yaml(section_text: str) -> Any:
    m = _YAML_FENCE_RE.search(section_text)
    if not m:
        return None
    return yaml.safe_load(m.group(1))


def parse_holdout_blocks(body: str) -> dict[str, Any]:
    """Extrahiert setup/test/teardown/evaluation_hint aus dem Holdout-Body."""
    sections = _extract_sections(body)
    result: dict[str, Any] = {}

    if "Setup" in sections:
        raw = _first_yaml(sections["Setup"])
        if raw is not None:
            result["setup"] = raw if isinstance(raw, list) else [raw]

    if "Test" in sections:
        raw = _first_yaml(sections["Test"])
        if isinstance(raw, dict):
            # Template schreibt { test: { action:..., assert:... } }
            result["test"] = raw.get("test", raw)

    if "Teardown" in sections:
        raw = _first_yaml(sections["Teardown"])
        if raw is not None:
            result["teardown"] = raw if isinstance(raw, list) else [raw]

    if "Evaluation Hint" in sections:
        result["evaluation_hint"] = sections["Evaluation Hint"].strip()

    return result


def is_structured_holdout(doc: Any) -> bool:
    """True wenn dieses Holdout das neue YAML-Format verwendet."""
    body = getattr(doc, "body", "") or ""
    blocks = parse_holdout_blocks(body)
    return "test" in blocks


# ── Variable Store ────────────────────────────────────────────────────────────

def _get_json_path(data: Any, path: str) -> Any:
    """Navigiert dot-separierte Pfade in einem dict/list, z.B. 'data.session_id'."""
    for key in path.split("."):
        if isinstance(data, dict):
            data = data.get(key)
        elif isinstance(data, list) and key.isdigit():
            data = data[int(key)]
        else:
            return None
    return data


class VariableStore:
    def __init__(self) -> None:
        self._vars: dict[str, Any] = {}

    def capture(self, captures: dict[str, str], response_data: Any) -> None:
        for var_name, json_path in captures.items():
            self._vars[var_name] = _get_json_path(response_data, json_path)

    def interpolate(self, value: Any) -> Any:
        """Ersetzt {captured.var} in Strings und rekursiv in dicts/lists."""
        if isinstance(value, str):
            return re.sub(
                r"\{captured\.(\w+)\}",
                lambda m: str(self._vars.get(m.group(1), m.group(0))),
                value,
            )
        if isinstance(value, dict):
            return {k: self.interpolate(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self.interpolate(v) for v in value]
        return value


# ── Assertions ────────────────────────────────────────────────────────────────

def _assert_value(path: str, actual: Any, expected: Any) -> str | None:
    """Gibt None zurück wenn die Assertion besteht, sonst Fehlermeldung."""
    if isinstance(expected, dict):
        if "present" in expected:
            if expected["present"] and actual is None:
                return f"{path}: key fehlt (erwartet: present)"
            if not expected["present"] and actual is not None:
                return f"{path}: key vorhanden (erwartet: absent)"
        elif "contains" in expected:
            if not isinstance(actual, str) or expected["contains"] not in actual:
                return f"{path}: '{actual}' enthält '{expected['contains']}' nicht"
        elif "matches" in expected:
            if not isinstance(actual, str) or not re.search(expected["matches"], actual):
                return f"{path}: '{actual}' matcht Regex '{expected['matches']}' nicht"
        elif "gt" in expected and not (actual is not None and actual > expected["gt"]):
            return f"{path}: {actual} > {expected['gt']} erwartet"
        elif "gte" in expected and not (actual is not None and actual >= expected["gte"]):
            return f"{path}: {actual} >= {expected['gte']} erwartet"
        elif "lt" in expected and not (actual is not None and actual < expected["lt"]):
            return f"{path}: {actual} < {expected['lt']} erwartet"
        elif "lte" in expected and not (actual is not None and actual <= expected["lte"]):
            return f"{path}: {actual} <= {expected['lte']} erwartet"
        elif "length" in expected:
            length = len(actual) if actual is not None else 0
            if length != expected["length"]:
                return f"{path}: Länge {length} != {expected['length']}"
        elif "min_length" in expected:
            length = len(actual) if actual is not None else 0
            if length < expected["min_length"]:
                return f"{path}: Länge {length} < {expected['min_length']}"
        elif "max_length" in expected:
            length = len(actual) if actual is not None else 0
            if length > expected["max_length"]:
                return f"{path}: Länge {length} > {expected['max_length']}"
    elif actual != expected:
        return f"{path}: {actual!r} != {expected!r}"
    return None


def check_http_assertions(
    status_code: int,
    body_data: Any,
    headers: dict[str, str],
    assert_spec: dict,
    store: VariableStore,
) -> list[str]:
    failures: list[str] = []

    expected_status = assert_spec.get("status")
    if expected_status is not None and status_code != expected_status:
        failures.append(f"status: {status_code} != {expected_status}")

    for path, expected in (assert_spec.get("body") or {}).items():
        actual = _get_json_path(body_data, path)
        f = _assert_value(path, actual, store.interpolate(expected))
        if f:
            failures.append(f)

    for header, expected in (assert_spec.get("headers") or {}).items():
        actual = headers.get(header) or headers.get(header.lower())
        f = _assert_value(f"header:{header}", actual, store.interpolate(expected))
        if f:
            failures.append(f)

    return failures


def check_cli_assertions(
    exit_code: int,
    stdout: str,
    stderr: str,
    assert_spec: dict,
) -> list[str]:
    failures: list[str] = []

    expected_exit = assert_spec.get("exit_code", 0)
    if exit_code != expected_exit:
        failures.append(f"exit_code: {exit_code} != {expected_exit}")

    for required in (assert_spec.get("stdout_contains") or []):
        if required not in stdout:
            failures.append(f"stdout: '{required}' nicht gefunden")

    for forbidden in (assert_spec.get("stdout_not_contains") or []):
        if forbidden in stdout:
            failures.append(f"stdout: '{forbidden}' unerwartet vorhanden")

    if assert_spec.get("stderr_empty") and stderr.strip():
        failures.append(f"stderr nicht leer: {stderr[:200]}")

    return failures


# ── Action Executor ───────────────────────────────────────────────────────────

@dataclass
class ActionResult:
    kind: str  # "http" | "cli" | "builtin"
    status_code: int | None = None
    body_data: Any = None
    body_text: str = ""
    headers: dict = field(default_factory=dict)
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    error: str = ""


class ActionExecutor:
    def __init__(
        self,
        base_url: str,
        store: VariableStore,
        runtime_cli: str = "docker",
        container_name: str | None = None,
        workspace: str = "/workspace",
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.store = store
        self.runtime_cli = runtime_cli
        self.container_name = container_name
        self.workspace = workspace
        self._http: Any = None  # lazy init

    def _get_http(self) -> Any:
        if self._http is None:
            import httpx
            self._http = httpx.Client(follow_redirects=True, timeout=15.0, verify=False)
        return self._http

    def close(self) -> None:
        if self._http is not None:
            self._http.close()

    def execute(self, action: dict) -> ActionResult:
        action = self.store.interpolate(action)
        if "builtin" in action:
            return self._run_builtin(action)
        if "method" in action:
            return self._run_http(action)
        if "command" in action:
            return self._run_cli(action)
        raise ValueError(f"Unbekannte Action: {action}")

    def _run_http(self, action: dict) -> ActionResult:
        method = action["method"].upper()
        url = self.base_url + action["path"]
        headers = action.get("headers") or {}
        body = action.get("body")
        try:
            http = self._get_http()
            resp = http.request(method, url, headers=headers,
                                json=body if body is not None else None)
            try:
                body_data = resp.json()
            except Exception:
                body_data = None
            return ActionResult(
                kind="http",
                status_code=resp.status_code,
                body_data=body_data,
                body_text=resp.text,
                headers=dict(resp.headers),
            )
        except Exception as exc:
            return ActionResult(kind="http", error=str(exc))

    def _run_cli(self, action: dict) -> ActionResult:
        cmd = [action["command"]] + (action.get("args") or [])
        cwd = action.get("cwd") or self.workspace
        env = action.get("env")

        import os
        if self.container_name:
            env_args: list[str] = []
            for k, v in (env or {}).items():
                env_args += ["-e", f"{k}={v}"]
            full_cmd = (
                [self.runtime_cli, "exec"] + env_args +
                [self.container_name, "sh", "-c",
                 f"cd {cwd} && " + " ".join(cmd)]
            )
            merged_env = None
        else:
            merged_env = {**os.environ, **(env or {})}
            full_cmd = cmd

        try:
            if self.container_name:
                r = subprocess.run(full_cmd, capture_output=True, text=True)
            else:
                r = subprocess.run(
                    full_cmd, capture_output=True, text=True,
                    cwd=cwd, env=merged_env,
                )
            return ActionResult(
                kind="cli",
                exit_code=r.returncode,
                stdout=r.stdout,
                stderr=r.stderr,
            )
        except Exception as exc:
            return ActionResult(kind="cli", error=str(exc))

    def _run_builtin(self, action: dict) -> ActionResult:
        builtin = action["builtin"]
        try:
            if builtin == "advance_time":
                seconds = action.get("seconds", 0)
                r = self._run_http({
                    "method": "POST",
                    "path": "/__test__/advance-time",
                    "body": {"seconds": seconds},
                })
                return ActionResult(kind="builtin", status_code=r.status_code)

            elif builtin == "write_file":
                path = action["path"]
                content = action.get("content", "")
                if self.container_name:
                    subprocess.run(
                        [self.runtime_cli, "exec", "-i", self.container_name,
                         "sh", "-c", f"mkdir -p $(dirname '{path}') && cat > '{path}'"],
                        input=content, text=True, check=True,
                    )
                else:
                    p = Path(path)
                    p.parent.mkdir(parents=True, exist_ok=True)
                    p.write_text(content, encoding="utf-8")
                return ActionResult(kind="builtin")

            elif builtin == "delete_file":
                path = action["path"]
                if self.container_name:
                    subprocess.run(
                        [self.runtime_cli, "exec", self.container_name,
                         "rm", "-f", path],
                        check=False,
                    )
                else:
                    Path(path).unlink(missing_ok=True)
                return ActionResult(kind="builtin")

            elif builtin == "wait":
                import time
                time.sleep(action.get("seconds", 1))
                return ActionResult(kind="builtin")

            else:
                return ActionResult(kind="builtin", error=f"Unbekanntes builtin: {builtin}")
        except Exception as exc:
            return ActionResult(kind="builtin", error=str(exc))


# ── Holdout Run Result ────────────────────────────────────────────────────────

@dataclass
class HoldoutRunResult:
    hol_id: str
    title: str
    spec: str
    contract: str
    priority: str
    passed: bool = False
    failures: list[str] = field(default_factory=list)
    setup_error: str = ""
    action_result: ActionResult | None = None
    task_delta: str = ""  # LLM-generierter Fix-Hinweis bei Fehler
    skipped: bool = False
    skip_reason: str = ""


# ── Runner ────────────────────────────────────────────────────────────────────

PRIORITY_ORDER = {"critical": 0, "normal": 1, "edge-case": 2}


def _run_steps(
    steps: list[dict],
    executor: ActionExecutor,
    store: VariableStore,
) -> str:
    """Führt eine Liste von Setup/Teardown-Schritten aus. Gibt Fehlermeldung oder '' zurück."""
    for step in steps:
        step_name = step.get("step", "?")
        action = step.get("action", {})
        captures = step.get("capture", {})
        result = executor.execute(action)
        if result.error:
            return f"Schritt '{step_name}' fehlgeschlagen: {result.error}"
        if captures and result.body_data is not None:
            store.capture(captures, result.body_data)
    return ""


def run_one_holdout(
    doc: Any,
    blocks: dict[str, Any],
    executor: ActionExecutor,
    store: VariableStore | None = None,
) -> HoldoutRunResult:
    """Führt einen einzelnen strukturierten Holdout aus."""
    fm = doc.frontmatter
    hol_id = fm.get("id", "?")
    title = fm.get("title", hol_id)
    priority = fm.get("priority", "normal")
    store = store or VariableStore()

    result = HoldoutRunResult(
        hol_id=hol_id,
        title=title,
        spec=fm.get("spec", ""),
        contract=fm.get("contract", ""),
        priority=priority,
    )

    # Setup
    setup_steps = blocks.get("setup") or []
    if setup_steps:
        err = _run_steps(setup_steps, executor, store)
        if err:
            result.passed = False
            result.setup_error = err
            _run_teardown(blocks, executor, store)
            return result

    # Test
    test_spec = blocks.get("test", {})
    action_def = test_spec.get("action", {})
    assert_spec = test_spec.get("assert", {})

    action_result = executor.execute(action_def)
    result.action_result = action_result

    if action_result.error:
        result.passed = False
        result.failures = [f"Action-Fehler: {action_result.error}"]
        _run_teardown(blocks, executor, store)
        return result

    # Assertions
    if action_result.kind == "http":
        result.failures = check_http_assertions(
            action_result.status_code or 0,
            action_result.body_data,
            action_result.headers,
            assert_spec,
            store,
        )
    elif action_result.kind == "cli":
        result.failures = check_cli_assertions(
            action_result.exit_code or 0,
            action_result.stdout,
            action_result.stderr,
            assert_spec,
        )

    result.passed = len(result.failures) == 0

    # Teardown immer
    _run_teardown(blocks, executor, store)

    return result


def _run_teardown(blocks: dict, executor: ActionExecutor, store: VariableStore) -> None:
    teardown_steps = blocks.get("teardown") or []
    if teardown_steps:
        _run_steps(teardown_steps, executor, store)


def run_structured_evaluation(
    config: Any,
    base_url: str,
    hol_ids: list[str] | None = None,
    spec_id: str | None = None,
    provider: Any = None,
    runtime_cli: str = "docker",
    container_name: str | None = None,
) -> "EvaluationReport":
    """Führt alle strukturierten aktiven Holdouts deterministisch aus.

    Reihenfolge: critical → normal → edge-case.
    Fail-fast: bei critical-Fehler werden normal und edge-case übersprungen.
    Bei normal-Fehler werden edge-case übersprungen.
    """
    from .evaluator import EvaluationReport, ScenarioResult, ScenarioRun
    from .frontmatter import parse_safe
    from datetime import datetime, timezone

    holdout_dir = config.holdout_dir
    docs = []
    if holdout_dir.exists():
        for md in sorted(holdout_dir.rglob("*.md")):
            doc = parse_safe(md)
            if not doc:
                continue
            fm = doc.frontmatter
            if not fm.get("id", "").startswith("HOL-"):
                continue
            if fm.get("status") != "active":
                continue
            if spec_id and fm.get("spec") != spec_id:
                continue
            if not is_structured_holdout(doc):
                continue
            docs.append(doc)

    if hol_ids:
        docs = [d for d in docs if d.frontmatter.get("id") in hol_ids]

    docs.sort(key=lambda d: PRIORITY_ORDER.get(d.frontmatter.get("priority", "normal"), 1))

    report = EvaluationReport(
        timestamp=datetime.now(timezone.utc).isoformat(),
        base_url=base_url,
    )

    executor = ActionExecutor(
        base_url=base_url,
        store=VariableStore(),
        runtime_cli=runtime_cli,
        container_name=container_name,
    )

    had_critical_failure = False
    had_normal_failure = False

    print(f"  {len(docs)} strukturierte Holdouts geladen", flush=True)

    try:
        for doc in docs:
            fm = doc.frontmatter
            hol_id = fm["id"]
            priority = fm.get("priority", "normal")

            # Fail-fast: skip nachgelagerte Prioritäten bei Fehler
            skip = False
            skip_reason = ""
            if had_critical_failure and priority in ("normal", "edge-case"):
                skip = True
                skip_reason = "critical-Fehler – übersprungen"
            elif had_normal_failure and priority == "edge-case":
                skip = True
                skip_reason = "normal-Fehler – edge-case übersprungen"

            print(f"  → {hol_id} [{priority}]: {fm.get('title', hol_id)}", flush=True)

            if skip:
                print(f"    ⊘ {skip_reason}", flush=True)
                scenario = _make_skipped_scenario(fm, skip_reason)
                report.scenarios.append(scenario)
                continue

            blocks = parse_holdout_blocks(doc.body)
            store = VariableStore()
            executor.store = store
            run_result = run_one_holdout(doc, blocks, executor, store)

            if not run_result.passed:
                if priority == "critical":
                    had_critical_failure = True
                elif priority == "normal":
                    had_normal_failure = True

                # LLM für Task-Delta wenn Provider verfügbar
                if provider and blocks.get("evaluation_hint"):
                    run_result.task_delta = _request_task_delta(
                        provider, run_result, blocks["evaluation_hint"]
                    )

            verdict = "✓ PASS" if run_result.passed else f"✗ FAIL: {'; '.join(run_result.failures[:2])}"
            print(f"    {verdict}", flush=True)

            scenario = _to_scenario_result(run_result)
            report.scenarios.append(scenario)
    finally:
        executor.close()

    return report


def _make_skipped_scenario(fm: dict, reason: str) -> Any:
    from .evaluator import ScenarioResult, ScenarioRun
    s = ScenarioResult(
        hol_id=fm["id"],
        title=fm.get("title", fm["id"]),
        contract=fm.get("contract", ""),
    )
    s.runs.append(ScenarioRun(
        run=1, passed=False,
        request={}, response_status=None, response_body=None,
        llm_verdict="skip", llm_reasoning=reason,
    ))
    return s


def _to_scenario_result(r: HoldoutRunResult) -> Any:
    from .evaluator import ScenarioResult, ScenarioRun
    scenario = ScenarioResult(
        hol_id=r.hol_id,
        title=r.title,
        contract=r.contract,
        pass_threshold=1,  # deterministischer Einzel-Run, kein Mehrheits-Threshold
    )

    action_details: dict = {}
    if r.action_result:
        ar = r.action_result
        if ar.kind == "http":
            action_details = {
                "method": "HTTP",
                "status": ar.status_code,
                "body": ar.body_text[:500] if ar.body_text else "",
            }
        elif ar.kind == "cli":
            action_details = {
                "exit_code": ar.exit_code,
                "stdout": ar.stdout[:500],
                "stderr": ar.stderr[:200],
            }

    reasoning = "; ".join(r.failures) if r.failures else (r.setup_error or "")
    if r.task_delta:
        reasoning += f"\n\nTask-Delta: {r.task_delta}"

    scenario.runs.append(ScenarioRun(
        run=1,
        passed=r.passed,
        request=action_details,
        response_status=r.action_result.status_code if r.action_result else None,
        response_body=r.action_result.body_text[:500] if r.action_result else None,
        llm_verdict="pass" if r.passed else "fail",
        llm_reasoning=reasoning or "OK",
    ))
    return scenario


def _request_task_delta(provider: Any, result: HoldoutRunResult, hint: str) -> str:
    """Einmaliger LLM-Aufruf: Evaluation Hint + Failures → konkreter Task-Delta."""
    failures_text = "\n".join(f"- {f}" for f in result.failures)
    prompt = (
        f"Holdout-Test '{result.hol_id}' ({result.title}) ist fehlgeschlagen.\n\n"
        f"Fehlgeschlagene Assertions:\n{failures_text}\n\n"
        f"Evaluation Hint (aus dem Holdout-Dokument):\n{hint}\n\n"
        "Aufgabe: Formuliere einen konkreten Task-Delta für den Implementierungs-Agenten. "
        "Nenne Datei, Funktion und was genau geändert werden muss. "
        "Antworte in 2–4 Sätzen, kein Markdown."
    )
    try:
        r = provider.complete(prompt, max_tokens=300)
        return r.text.strip()
    except Exception as exc:
        return f"(Task-Delta nicht verfügbar: {exc})"
