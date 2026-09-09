"""Eigenständiger Evaluator für Holdout-Szenarien (Dark Factory Pattern).

Architektur-Invariante: Dieser Prozess hat KEINEN Zugriff auf den Sourcecode.
Er liest nur HOL-Dokumente aus .sdd/holdout/ und sendet HTTP-Requests gegen
einen konfigurierbaren base_url.

Ablauf pro Szenario:
  1. LLM leitet HTTP-Request aus Plain-English-Beschreibung ab
  2. Request wird gegen base_url ausgeführt
  3. LLM bewertet Response (Szenario erfüllt? ja/nein)
  4. 3 Runs, min. 2/3 müssen bestehen
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import SddConfig
from .frontmatter import parse_safe
from .llm.base import CompletionProvider


PASS_THRESHOLD = 2

# Wiederholungen pro Legacy-Szenario. Default 1 statt bisher 3.
#
# Der Legacy-Pfad setzt den Zustand zwischen den Laeufen nicht zurueck. Jedes
# Szenario, das etwas anlegt, gelingt in Lauf 1 und scheitert in 2 und 3 an dem,
# was Lauf 1 hinterlassen hat — und ein Szenario, das einen Konflikt erwartet,
# besteht ab Lauf 2 aus dem falschen Grund. Drei Laeufe ohne Reset messen also
# nicht die Stabilitaet der Implementierung, sondern nur, ob das Szenario
# idempotent ist.
#
# Ueber evaluator.runs_per_scenario weiter erhoehbar, sobald eine Isolierung
# existiert. Der Schluessel stand schon in der config.yaml und wurde bis hierher
# nie gelesen.
DEFAULT_RUNS_PER_SCENARIO = 1
RUNS_PER_SCENARIO = 3  # historischer Wert, nur noch fuer bestehende Aufrufer


@dataclass
class ScenarioRun:
    run: int
    passed: bool
    request: dict[str, Any]
    response_status: int | None
    response_body: str | None
    llm_verdict: str
    llm_reasoning: str


@dataclass
class ScenarioResult:
    hol_id: str
    title: str
    contract: str
    runs: list[ScenarioRun] = field(default_factory=list)
    pass_threshold: int = PASS_THRESHOLD  # 1 für deterministische Runs, 2 für LLM-Runs
    priority: str = "normal"
    task_delta: str | None = None

    @property
    def passed(self) -> bool:
        return sum(1 for r in self.runs if r.passed) >= self.pass_threshold

    @property
    def pass_count(self) -> int:
        return sum(1 for r in self.runs if r.passed)


@dataclass
class EvaluationReport:
    timestamp: str
    base_url: str
    scenarios: list[ScenarioResult] = field(default_factory=list)
    # Wegen status ausgeschlossene Szenarien, nach Statuswert. Ohne diese Zahl
    # ist ein leerer Lauf nicht von "keine Szenarien vorhanden" unterscheidbar.
    skipped_by_status: dict[str, int] = field(default_factory=dict)

    @property
    def total(self) -> int:
        return len(self.scenarios)

    @property
    def passed(self) -> int:
        return sum(1 for s in self.scenarios if s.passed)

    @property
    def pass_rate(self) -> float:
        return (self.passed / self.total) if self.total else 0.0

    def to_dict(self) -> dict:
        tier_summary: dict[str, dict[str, int]] = {
            "critical":  {"passed": 0, "failed": 0, "skipped": 0},
            "normal":    {"passed": 0, "failed": 0, "skipped": 0},
            "edge-case": {"passed": 0, "failed": 0, "skipped": 0},
        }
        for s in self.scenarios:
            tier = getattr(s, "priority", "normal") or "normal"
            bucket = tier_summary.get(tier, tier_summary["normal"])
            if any(r.llm_verdict == "skip" for r in s.runs):
                bucket["skipped"] += 1
            elif s.passed:
                bucket["passed"] += 1
            else:
                bucket["failed"] += 1

        d = {
            "timestamp": self.timestamp,
            "base_url": self.base_url,
            "tier_summary": tier_summary,
            "summary": {
                "total": self.total,
                "passed": self.passed,
                "failed": self.total - self.passed,
                "pass_rate": round(self.pass_rate, 4),
                "skipped_by_status": dict(self.skipped_by_status),
            },
            "scenarios": [],
        }
        for s in self.scenarios:
            d["scenarios"].append({
                "hol_id": s.hol_id,
                "title": s.title,
                "contract": s.contract,
                "passed": s.passed,
                "pass_count": s.pass_count,
                "priority": getattr(s, "priority", "normal") or "normal",
                "task_delta": getattr(s, "task_delta", None),
                "runs": [asdict(r) for r in s.runs],
            })
        return d


_EVAL_STATUSES = {"active", "ready"}


def _load_holdout_docs(config: SddConfig, spec_id: str | None = None) -> list:
    docs, _ = _load_holdout_docs_with_skips(config, spec_id)
    return docs


def _load_holdout_docs_with_skips(
    config: SddConfig, spec_id: str | None = None
) -> tuple[list, dict[str, int]]:
    """Laedt evaluierbare HOL-Dokumente und zaehlt die wegen Status verworfenen.

    Die Zaehlung ist noetig, weil ein Szenario mit `status: wip` sonst spurlos
    verschwindet: der Lauf meldet 0 Szenarien, und dass ueberhaupt welche da
    waren, sieht niemand. Die Templates erzeugten genau diesen Status.
    """
    docs: list = []
    skipped: dict[str, int] = {}
    if not config.holdout_dir.exists():
        return docs, skipped
    for md in sorted(config.holdout_dir.rglob("*.md")):
        doc = parse_safe(md)
        if not doc:
            continue
        fm = doc.frontmatter
        if not fm.get("id", "").startswith("HOL-"):
            continue
        if spec_id and fm.get("spec") != spec_id:
            continue
        status = fm.get("status", "active")
        if status not in _EVAL_STATUSES:
            skipped[status] = skipped.get(status, 0) + 1
            continue
        docs.append(doc)
    return docs, skipped


def _build_plan_prompt(scenario_title: str, scenario_body: str, base_url: str) -> str:
    return f"""You are an API test planner. Your task is to derive a single HTTP request
from the following plain-English scenario description. The service runs at: {base_url}

Scenario: {scenario_title}

{scenario_body}

Respond with a JSON object and nothing else. Format:
{{
  "method": "GET|POST|PUT|PATCH|DELETE",
  "path": "/api/...",
  "headers": {{}},
  "body": null
}}"""


def _build_eval_prompt(scenario_title: str, scenario_body: str,
                       request: dict, response_status: int, response_body: str) -> str:
    return f"""You are a neutral evaluator. Decide if the HTTP response satisfies the scenario.

Scenario: {scenario_title}
{scenario_body}

Request sent:
{json.dumps(request, indent=2)}

Response:
Status: {response_status}
Body: {response_body[:2000]}

Answer with a JSON object and nothing else:
{{
  "passed": true|false,
  "reasoning": "<one sentence>"
}}"""


def _call_llm(provider: CompletionProvider, prompt: str) -> dict:
    """Ruft den LLM-Provider auf und gibt das geparste JSON zurück."""
    result = provider.complete(prompt)
    raw = result.text.strip()
    # Robustes JSON-Parsing: extrahiere erstes {...}-Block
    start = raw.find("{")
    end = raw.rfind("}") + 1
    return json.loads(raw[start:end])


def _run_scenario_once(
    run_num: int,
    title: str,
    body: str,
    base_url: str,
    http: "httpx.Client",
    provider: CompletionProvider,
) -> ScenarioRun:
    # Schritt 1: LLM plant HTTP-Request
    plan_prompt = _build_plan_prompt(title, body, base_url)
    try:
        request_plan = _call_llm(provider, plan_prompt)
    except Exception as exc:
        return ScenarioRun(
            run=run_num, passed=False,
            request={}, response_status=None, response_body=None,
            llm_verdict="error", llm_reasoning=f"LLM-Planungsfehler: {exc}",
        )

    method = request_plan.get("method", "GET").upper()
    path = request_plan.get("path", "/")
    headers = request_plan.get("headers") or {}
    body_payload = request_plan.get("body")

    # Schritt 2: HTTP-Request ausführen
    url = base_url.rstrip("/") + path
    try:
        resp = http.request(method, url, headers=headers,
                            json=body_payload if body_payload else None,
                            timeout=10.0)
        status_code = resp.status_code
        resp_body = resp.text
    except Exception as exc:
        return ScenarioRun(
            run=run_num, passed=False,
            request=request_plan, response_status=None, response_body=None,
            llm_verdict="error", llm_reasoning=f"HTTP-Fehler: {exc}",
        )

    # Schritt 3: LLM bewertet Response
    eval_prompt = _build_eval_prompt(title, body, request_plan, status_code, resp_body)
    try:
        verdict = _call_llm(provider, eval_prompt)
        passed = bool(verdict.get("passed", False))
        reasoning = verdict.get("reasoning", "")
    except Exception as exc:
        passed = False
        reasoning = f"LLM-Evaluierungsfehler: {exc}"

    return ScenarioRun(
        run=run_num, passed=passed,
        request=request_plan, response_status=status_code, response_body=resp_body,
        llm_verdict="pass" if passed else "fail", llm_reasoning=reasoning,
    )


def run_evaluation(
    config: SddConfig,
    base_url: str,
    hol_ids: list[str] | None = None,
    spec_id: str | None = None,
    container_name: str | None = None,
    tier_filter: str | None = None,
) -> EvaluationReport:
    """Führt alle aktiven HOL-Szenarien gegen base_url aus.

    Strukturierte Holdouts (neues YAML-Format) werden deterministisch ausgeführt.
    Legacy-Holdouts (Prosa) nutzen den LLM-Pfad (3 Runs, LLM plant + bewertet).
    """
    from .holdout_runner import is_structured_holdout, run_structured_evaluation

    all_docs, skipped_by_status = _load_holdout_docs_with_skips(config, spec_id=spec_id)
    if hol_ids:
        all_docs = [d for d in all_docs if d.frontmatter.get("id") in hol_ids]

    structured_docs = [d for d in all_docs if is_structured_holdout(d)]
    legacy_docs = [d for d in all_docs if not is_structured_holdout(d)]

    print(f"  {len(structured_docs)} strukturierte + {len(legacy_docs)} Legacy-Holdouts", flush=True)
    if legacy_docs:
        # Die Einschraenkung steht nirgends, wo ein Autor sie sieht: der
        # Legacy-Pfad plant genau eine Anfrage pro Lauf und kennt weder Setup
        # noch Teardown. Mehrschrittige Prosa-Szenarien koennen deshalb nicht
        # bestehen — ohne Hinweis sucht man den Fehler in der Implementierung.
        print(
            "  [Legacy] Prosa-Holdouts fuehren genau eine Anfrage pro Lauf aus und "
            "kennen kein Setup/Teardown.\n"
            "           Mehrschrittige Szenarien brauchen das strukturierte Format.",
            flush=True,
        )
    if skipped_by_status:
        detail = ", ".join(f"{n}x status: {st}" for st, n in sorted(skipped_by_status.items()))
        print(f"  {sum(skipped_by_status.values())} Szenario(en) uebersprungen ({detail})",
              flush=True)

    # Strukturierte Holdouts: deterministisch
    from .dev_container import resolve_runtime
    docker_runtime = resolve_runtime(config.raw)

    struct_report = run_structured_evaluation(
        config, base_url,
        hol_ids=hol_ids,
        spec_id=spec_id,
        provider=None,  # nur bei Fehlern benötigt; wird lazy geladen
        runtime_cli=docker_runtime,
        container_name=container_name,
        tier_filter=tier_filter,
    ) if structured_docs else None

    # Legacy-Holdouts: LLM-Pfad
    if legacy_docs:
        legacy_report = _run_legacy_evaluation(
            config, base_url, legacy_docs, tier_filter=tier_filter)
    else:
        legacy_report = None

    # Reports zusammenführen
    report = EvaluationReport(
        timestamp=datetime.now(timezone.utc).isoformat(),
        base_url=base_url,
        skipped_by_status=skipped_by_status,
    )
    if struct_report:
        report.scenarios.extend(struct_report.scenarios)
    if legacy_report:
        report.scenarios.extend(legacy_report.scenarios)

    return report


def _legacy_runs_per_scenario(config: SddConfig) -> int:
    """Anzahl Wiederholungen pro Legacy-Szenario aus der Konfiguration."""
    raw = (config.raw.get("evaluator") or {}).get(
        "runs_per_scenario", DEFAULT_RUNS_PER_SCENARIO)
    try:
        return max(1, int(raw))
    except (TypeError, ValueError):
        return DEFAULT_RUNS_PER_SCENARIO


def _majority_threshold(runs: int) -> int:
    """Mehrheit der Laeufe, mindestens 1.

    Mit PASS_THRESHOLD = 2 konnte ein Einzellauf nie bestehen — der Wert war auf
    genau drei Laeufe zugeschnitten.
    """
    return 1 if runs <= 1 else (runs // 2) + 1


def _run_legacy_evaluation(
    config: SddConfig,
    base_url: str,
    docs: list,
    tier_filter: str | None = None,
) -> EvaluationReport:
    """Legacy LLM-Pfad für Prosa-Holdouts (LLM plant + bewertet).

    Tier-Filter, priority und Fail-Fast waren ausschliesslich im strukturierten
    Pfad umgesetzt (SPEC-0042 FR-01/FR-02/FR-04). Der Legacy-Pfad bekam den
    Filter gar nicht erst uebergeben: `--tier critical` fuehrte alle Szenarien
    aus, und jedes Ergebnis trug priority "normal", womit tier_summary die
    Staffelung nicht auswerten konnte.
    """
    from .holdout_runner import PRIORITY_ORDER, _make_skipped_scenario
    from .llm import get_completion_provider
    provider = get_completion_provider(config, "evaluator")

    runs_per_scenario = _legacy_runs_per_scenario(config)

    if tier_filter is not None:
        docs = [d for d in docs
                if d.frontmatter.get("priority", "normal") == tier_filter]
    docs = sorted(docs, key=lambda d: PRIORITY_ORDER.get(
        d.frontmatter.get("priority", "normal"), 1))

    had_critical_failure = False
    had_normal_failure = False

    report = EvaluationReport(
        timestamp=datetime.now(timezone.utc).isoformat(),
        base_url=base_url,
    )

    try:
        import httpx
    except ImportError as e:
        raise RuntimeError(
            "Das httpx-Paket ist nicht installiert. "
            "Führe `pip install 'sdd-cli[evaluate]'` aus."
        ) from e

    import urllib.parse
    _parsed = urllib.parse.urlparse(base_url)
    _verify = _parsed.hostname not in ("localhost", "127.0.0.1", "::1")

    with httpx.Client(follow_redirects=True, verify=_verify) as http:
        for doc in docs:
            fm = doc.frontmatter
            hol_id = fm["id"]
            title = fm.get("title", hol_id)
            contract = fm.get("contract", "")
            body_text = doc.body.strip()

            priority = fm.get("priority", "normal")

            # Fail-Fast wie im strukturierten Pfad: nachgelagerte Prioritaeten
            # entfallen nach einem Fehlschlag. Bei gesetztem tier_filter greift
            # es nicht, weil dann ohnehin nur eine Stufe laeuft.
            skip_reason = ""
            if tier_filter is not None:
                pass
            elif had_critical_failure and priority in ("normal", "edge-case"):
                skip_reason = "critical-Fehler – übersprungen"
            elif had_normal_failure and priority == "edge-case":
                skip_reason = "normal-Fehler – edge-case übersprungen"

            print(f"  → {hol_id} [legacy · {priority}]: {title}", flush=True)

            if skip_reason:
                print(f"    ⊘ {skip_reason}", flush=True)
                report.scenarios.append(_make_skipped_scenario(fm, skip_reason))
                continue

            result = ScenarioResult(
                hol_id=hol_id, title=title, contract=contract,
                priority=priority,
                pass_threshold=_majority_threshold(runs_per_scenario),
            )
            for i in range(1, runs_per_scenario + 1):
                print(f"    Run {i}/{runs_per_scenario} …", flush=True)
                run = _run_scenario_once(i, title, body_text, base_url, http, provider)
                verdict = "✓" if run.passed else "✗"
                print(f"    Run {i} {verdict}  {run.llm_reasoning[:80]}", flush=True)
                result.runs.append(run)

            if not result.passed:
                if priority == "critical":
                    had_critical_failure = True
                elif priority == "normal":
                    had_normal_failure = True

            status = "PASS" if result.passed else "FAIL"
            print(f"  {hol_id}: {status} ({result.pass_count}/{len(result.runs)})", flush=True)
            if 0 < result.pass_count < len(result.runs):
                # Uneinheitliche Laeufe deuten fast immer auf fehlenden
                # Zustands-Reset hin, nicht auf Flakiness der Implementierung.
                print(
                    f"    ⚠ Laeufe gehen unterschiedlich aus. Der Legacy-Pfad setzt "
                    f"den Zustand zwischen Laeufen nicht zurueck — Lauf 1 kann "
                    f"Lauf 2 beeinflussen.",
                    flush=True,
                )
            report.scenarios.append(result)

    return report


def persist_report(config: SddConfig, report: EvaluationReport) -> Path:
    """Speichert den Report als JSON in .sdd/evaluations/."""
    config.evaluations_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d-%H%M%S")
    path = config.evaluations_dir / f"{ts}.json"
    path.write_text(json.dumps(report.to_dict(), indent=2, ensure_ascii=False),
                    encoding="utf-8")
    return path
