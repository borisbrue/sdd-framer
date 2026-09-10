"""Orchestrator – lokale Dark-Factory-Pipeline.

Ablauf pro Attempt:
  1. Spec + AGENTS.md + Contracts laden (OHNE .sdd/holdout/)
  2. Code-Generierung via Claude
  3. Dateien schreiben
  4. git: Branch + Commit
  5. Build-Kommando ausführen (optional)
  6. PR erstellen via gh CLI (optional)
  7. Evaluator laufen lassen (optional)
  8. Bei Pass (≥ 90 %): PR labeln / mergen
     Bei Fail: Retry mit angereichertem Fehlerkontext (max. --max-retries)
"""
from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import SddConfig
from .frontmatter import parse_safe

DEFAULT_MAX_RETRIES = 3
BRANCH_PREFIX = "sdd"
LABEL_APPROVED = "sdd:approved"
LABEL_FAILED = "sdd:failed"
LABEL_COST_LIMIT = "sdd:cost-limit"


@dataclass
class PipelineAttempt:
    attempt: int
    branch: str
    build_passed: bool | None
    eval_pass_rate: float | None
    pr_url: str | None
    error: str | None
    explanation: str


@dataclass
class PipelineReport:
    timestamp: str
    spec_id: str
    final_status: str   # "merged" | "labeled" | "failed" | "dry_run"
    attempts: list[PipelineAttempt] = field(default_factory=list)
    issue_url: str | None = None

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "spec_id": self.spec_id,
            "final_status": self.final_status,
            "issue_url": self.issue_url,
            "attempts": [asdict(a) for a in self.attempts],
        }


# ─── Context-Loader ──────────────────────────────────────────────────────────

def _load_spec(config: SddConfig, spec_id: str) -> str:
    for md in config.specs_dir.rglob("*.md"):
        doc = parse_safe(md)
        if doc and doc.frontmatter.get("id") == spec_id:
            return md.read_text(encoding="utf-8")
    raise ValueError(f"Spec nicht gefunden: {spec_id}")


def _load_agents_md(config: SddConfig) -> str:
    agents = config.root / "AGENTS.md"
    if agents.exists():
        return agents.read_text(encoding="utf-8")
    return ""


def _load_contracts(config: SddConfig, spec_id: str) -> list[tuple[str, str]]:
    """Gibt [(contract_id, inhalt)] für alle Contracts der Spec zurück."""
    for md in config.specs_dir.rglob("*.md"):
        doc = parse_safe(md)
        if doc and doc.frontmatter.get("id") == spec_id:
            contract_ids = doc.frontmatter.get("contracts") or []
            break
    else:
        return []

    result = []
    for cid in contract_ids:
        for md in config.contracts_dir.rglob("*.md"):
            doc = parse_safe(md)
            if doc and doc.frontmatter.get("id") == cid:
                result.append((cid, md.read_text(encoding="utf-8")))
                break
    return result


def _build_code_gen_prompt(spec_content: str, agents_md: str,
                            contracts: list[tuple[str, str]],
                            prev_error_context: str) -> str:
    parts = [
        "You are an expert software engineer. Implement the feature described in the spec below.",
        "Return ONLY a JSON object — no markdown fences, no prose — in this exact format:",
        '{ "files": [ { "path": "relative/path/to/file", "content": "..." } ], "explanation": "<one line>" }',
        "",
    ]

    if agents_md:
        parts += ["## Repository Context (AGENTS.md)", agents_md, ""]

    parts += ["## Feature Spec", spec_content, ""]

    for cid, content in contracts:
        parts += [f"## Contract: {cid}", content, ""]

    if prev_error_context:
        parts += [
            "## Previous Attempt Failed — Fix These Issues",
            prev_error_context,
            "",
        ]

    parts.append("Implement the spec. Write production-quality code. No placeholder comments.")
    return "\n".join(parts)


# ─── LLM + subprocess helpers ────────────────────────────────────────────────

def _call_code_gen_agent(
    config: SddConfig,
    spec_id: str,
    spec_content: str,
    agents_md: str,
    contracts: list[tuple[str, str]],
    error_context: str,
    timeout: int = 600,
    on_proc: Callable[[subprocess.Popen], None] | None = None,
) -> tuple[list[dict[str, Any]], str]:
    """Führt Code-Generierung via konfiguriertem Provider aus.
    Returns (files_list, explanation)."""
    from .llm import get_code_gen_provider
    parts = [
        f"Implement the software feature described in spec {spec_id}.",
        "Write all necessary source code files directly into this project.",
        "Do NOT modify any .md files under specs/, contracts/, or tests/.",
        "",
    ]
    if agents_md:
        parts += ["## Repository Guidelines", agents_md, ""]
    parts += ["## Spec", spec_content, ""]
    for cid, content in contracts:
        parts += [f"## Contract: {cid}", content, ""]
    if error_context:
        parts += ["## Previous Attempt Failed — Fix These Issues", error_context, ""]
    parts.append("Implement the spec now. Write production-quality code.")
    prompt = "\n".join(parts)

    provider = get_code_gen_provider(config)
    return provider.generate(prompt, config.root, timeout=timeout, on_proc=on_proc)


def _run(cmd: list[str] | str, cwd: Path,
         shell: bool = False) -> tuple[int, str]:
    result = subprocess.run(
        cmd, cwd=cwd, shell=shell, capture_output=True, text=True,
    )
    return result.returncode, (result.stdout + result.stderr).strip()


def _git(args: list[str], cwd: Path) -> tuple[int, str]:
    return _run(["git"] + args, cwd)


def _gh_available() -> bool:
    try:
        rc, _ = _run(["gh", "--version"], Path("."))
        return rc == 0
    except FileNotFoundError:
        return False


# ─── Pipeline ────────────────────────────────────────────────────────────────

def _write_files(config: SddConfig, files: list[dict]) -> None:
    for f in files:
        path = config.root / f["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f["content"], encoding="utf-8")


def _create_branch_and_commit(config: SddConfig, branch: str,
                               spec_id: str, explanation: str) -> None:
    _git(["checkout", "-b", branch], config.root)
    _git(["add", "-A"], config.root)
    _git(["commit", "-m", f"feat({spec_id}): {explanation}"], config.root)


def _create_pr(config: SddConfig, branch: str, spec_id: str,
               explanation: str) -> str | None:
    if not _gh_available():
        return None
    rc, out = _run(
        ["gh", "pr", "create",
         "--title", f"feat({spec_id}): {explanation}",
         "--body", f"Auto-generated by `sdd orchestrate --spec {spec_id}`\n\n{explanation}",
         "--head", branch],
        cwd=config.root,
    )
    if rc != 0:
        return None
    for line in out.splitlines():
        if line.startswith("https://"):
            return line.strip()
    return out.strip() or None


def _label_pr(config: SddConfig, pr_url: str, label: str) -> None:
    if not _gh_available() or not pr_url:
        return
    _run(["gh", "pr", "edit", pr_url, "--add-label", label], config.root)


def _merge_pr(config: SddConfig, pr_url: str, strategy: str) -> None:
    if not _gh_available() or not pr_url:
        return
    if strategy == "direct":
        _run(["gh", "pr", "merge", pr_url, "--squash"], config.root)
    else:
        _run(["gh", "pr", "merge", pr_url, "--squash", "--auto"], config.root)


def _open_failure_issue(config: SddConfig, spec_id: str, pr_url: str | None,
                        last_eval_context: str) -> str | None:
    if not _gh_available():
        return None
    title = f"[SDD] Auto-Merge fehlgeschlagen: feat({spec_id})"
    body = (
        f"Der Orchestrator hat nach allen Retry-Versuchen keinen passenden Code "
        f"erzeugt.\n\n"
        f"**PR:** {pr_url or '—'}\n\n"
        f"**Letzter Evaluator-Report:**\n```\n{last_eval_context[:3000]}\n```\n\n"
        f"Starte einen neuen Zyklus mit: `sdd orchestrate --spec {spec_id} --resume`"
    )
    rc, out = _run(["gh", "issue", "create", "--title", title, "--body", body], config.root)
    if rc != 0:
        return None
    for line in out.splitlines():
        if line.startswith("https://"):
            return line.strip()
    return out.strip() or None


def run_pipeline(
    config: SddConfig,
    spec_id: str,
    base_url: str | None = None,
    build_cmd: str | None = None,
    max_retries: int = DEFAULT_MAX_RETRIES,
    no_pr: bool = False,
    dry_run: bool = False,
    project_id: str = "",
    on_step: Callable[[str], None] | None = None,
    on_proc: Callable[[subprocess.Popen], None] | None = None,
    is_aborted: Callable[[], bool] | None = None,
) -> PipelineReport:
    def _step(msg: str) -> None:
        if on_step:
            on_step(msg)
    from .autonomy import auto_merge_allowed, record_pr_result
    from .evaluator import run_evaluation  # avoid circular at module level

    orch_cfg = config.raw.get("orchestrator", {})
    auto_merge_enabled = orch_cfg.get("auto_merge", False)
    auto_merge_strategy = orch_cfg.get("auto_merge_strategy", "label")
    effective_build_cmd = build_cmd or orch_cfg.get("build_command", "")
    code_gen_timeout = int(orch_cfg.get("code_gen_timeout", 600))

    # Der Build laeuft in der Finalisierung, im Dev-Container vor den Tests (#111).

    # Track base branch so we can reset between attempts
    _, _base = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"], config.root)
    base_branch = _base.strip() or "main"

    report = PipelineReport(
        timestamp=datetime.now(timezone.utc).isoformat(),
        spec_id=spec_id,
        final_status="failed",
    )

    spec_content = _load_spec(config, spec_id)
    agents_md = _load_agents_md(config)
    contracts = _load_contracts(config, spec_id)

    if dry_run:
        _step("Dry-run: Code wird generiert…")
        files_dr, explanation_dr = _call_code_gen_agent(
            config, spec_id, spec_content, agents_md, contracts, "",
            timeout=code_gen_timeout, on_proc=on_proc,
        )
        _step(f"✓ Dry-run: {len(files_dr)} Datei(en) generiert — {explanation_dr[:60]}")
        # Undo agent's changes (no commit in dry_run)
        _git(["reset", "--hard", "HEAD"], config.root)
        _run(["git", "clean", "-fd"], config.root)
        report.final_status = "dry_run"
        report.attempts.append(PipelineAttempt(
            attempt=1, branch=f"{BRANCH_PREFIX}/{spec_id}-attempt-1",
            build_passed=None, eval_pass_rate=None, pr_url=None,
            error=None, explanation=explanation_dr,
        ))
        return report

    error_context = ""
    last_pr_url: str | None = None
    last_eval_context = ""

    for attempt_num in range(1, max_retries + 1):
        branch = f"{BRANCH_PREFIX}/{spec_id}-attempt-{attempt_num}"

        # Abort check at the start of each attempt
        if is_aborted and is_aborted():
            report.final_status = "aborted"
            break

        # Ensure clean working tree on base branch before each attempt
        _git(["checkout", base_branch], config.root)
        _git(["reset", "--hard", "HEAD"], config.root)
        _run(["git", "clean", "-fd"], config.root)
        _step(f"Code wird generiert… (Attempt {attempt_num}/{max_retries})")

        # 1. Code generieren — agent writes files to config.root directly
        try:
            files, explanation = _call_code_gen_agent(
                config, spec_id, spec_content, agents_md, contracts,
                error_context, timeout=code_gen_timeout, on_proc=on_proc,
            )
        except Exception as exc:
            if is_aborted and is_aborted():
                _step("⊘ Pipeline abgebrochen")
                report.final_status = "aborted"
                break
            _step(f"✗ Code-Generierung fehlgeschlagen: {exc}")
            report.attempts.append(PipelineAttempt(
                attempt=attempt_num, branch=branch,
                build_passed=None, eval_pass_rate=None, pr_url=None,
                error=str(exc), explanation="",
            ))
            error_context = f"Code generation failed: {exc}"
            continue

        _step(f"✓ {len(files)} Datei(en) generiert — {explanation[:80]}")

        # 2. Git Branch + Commit (files already on disk)
        _create_branch_and_commit(config, branch, spec_id, explanation)
        _step(f"✓ Branch {branch} committed")

        # 4. Container-Test + PR via SpecFinalizer (einheitliche Finalisierung)
        _step(f"Container-Test läuft… (Attempt {attempt_num}/{max_retries})")
        from .finalize import SpecFinalizer
        finalizer = SpecFinalizer(config, dry_run=dry_run)
        try:
            fin_report = finalizer.run(
                spec_id,
                no_commit=True,   # Branch + Commit bereits oben erledigt
                branch=branch,
                build_cmd=effective_build_cmd or None,
            )
        except RuntimeError as exc:
            _step(f"✗ Finalisierung fehlgeschlagen: {exc}")
            report.attempts.append(PipelineAttempt(
                attempt=attempt_num, branch=branch,
                build_passed=None, eval_pass_rate=None, pr_url=None,
                error=str(exc), explanation=explanation,
            ))
            error_context = str(exc)
            continue

        build_passed: bool | None = fin_report.tests_passed
        if fin_report.build_passed is False:
            # Wie vor 45b29e6: der naechste Versuch bekommt die Build-Ausgabe als
            # Fehlerkontext. Ein leeres test_output haette der Code-Generierung
            # nicht gesagt, was sie reparieren soll (#111).
            _step(f"✗ Build fehlgeschlagen (Attempt {attempt_num})")
            error_context = f"Build failed (attempt {attempt_num}):\n{fin_report.build_output}"
            report.attempts.append(PipelineAttempt(
                attempt=attempt_num, branch=branch,
                build_passed=False, eval_pass_rate=None, pr_url=None,
                error=fin_report.build_output[:1000], explanation=explanation,
            ))
            continue
        if not fin_report.tests_passed:
            _step(f"✗ Container-Tests fehlgeschlagen (Attempt {attempt_num})")
            error_context = fin_report.test_output
            report.attempts.append(PipelineAttempt(
                attempt=attempt_num, branch=branch,
                build_passed=False, eval_pass_rate=None, pr_url=None,
                error=fin_report.test_output[:1000], explanation=explanation,
            ))
            continue
        _step("✓ Container-Tests grün")

        pr_url: str | None = fin_report.pr_url if not no_pr else None
        if pr_url:
            last_pr_url = pr_url
            _step(f"✓ PR erstellt: {pr_url}")
        elif not no_pr:
            _step("PR-Erstellung übersprungen (gh nicht verfügbar oder lokal)")

        # 6. Evaluator (optional)
        _step(f"Evaluator läuft… (Attempt {attempt_num}/{max_retries})")
        eval_pass_rate: float | None = None
        eval_context = ""
        if base_url:
            eval_report = run_evaluation(config, base_url)
            eval_pass_rate = eval_report.pass_rate
            pct = f"{eval_pass_rate:.0%}"
            if eval_pass_rate < 0.9:
                _step(f"✗ Evaluator: {pct} — nicht bestanden (Attempt {attempt_num})")
                failed_rows = [
                    f"| {s.hol_id} | {s.title} | {s.pass_count}/{len(s.runs)} runs |"
                    f" {s.runs[-1].llm_reasoning[:80] if s.runs else ''} |"
                    for s in eval_report.scenarios if not s.passed
                ]
                eval_context = (
                    f"## Vorheriger Versuch fehlgeschlagen (Attempt {attempt_num})\n\n"
                    f"Folgende Holdout-Szenarien sind nicht bestanden:\n\n"
                    f"| HOL-ID | Titel | Runs | Fehlschlag-Grund |\n"
                    f"|--------|-------|------|------------------|\n"
                    + "\n".join(failed_rows)
                    + "\n\nBitte korrigiere den Code so, dass alle obigen Szenarien bestehen."
                )
                last_eval_context = eval_context
            else:
                _step(f"✓ Evaluator: {pct} — bestanden")

        # 7. Ergebnis auswerten
        passed = (eval_pass_rate is None) or (eval_pass_rate >= 0.9)
        report.attempts.append(PipelineAttempt(
            attempt=attempt_num, branch=branch,
            build_passed=build_passed, eval_pass_rate=eval_pass_rate,
            pr_url=pr_url, error=None if passed else eval_context[:500],
            explanation=explanation,
        ))

        if passed:
            # PR-Ergebnis in evaluations.db schreiben (für Autonomy Level)
            if project_id:
                pr_number = (pr_url or branch).split("/")[-1]
                record_pr_result(
                    config, project_id, pr_number,
                    passed=True,
                    pass_rate=eval_pass_rate if eval_pass_rate is not None else 1.0,
                )

            if pr_url and auto_merge_enabled:
                # Autonomy-Level-Check vor Auto-Merge
                from .projects import load_project
                project = load_project(config, project_id) if project_id else None
                autonomy_level = project.autonomy_level if project else 1.0
                from .autonomy import compute_level_stats
                stats = compute_level_stats(config, project_id or "", autonomy_level)
                allowed, reason = auto_merge_allowed(
                    config, project_id or "", autonomy_level,
                    stats.total_prs, eval_pass_rate or 1.0,
                )
                if allowed:
                    _label_pr(config, pr_url, LABEL_APPROVED)
                    if auto_merge_strategy == "direct":
                        _merge_pr(config, pr_url, "direct")
                    report.final_status = "merged" if auto_merge_strategy == "direct" else "labeled"
                else:
                    _label_pr(config, pr_url, LABEL_APPROVED)
                    report.final_status = "labeled"
            elif pr_url:
                _label_pr(config, pr_url, LABEL_APPROVED)
                report.final_status = "labeled"
            else:
                report.final_status = "labeled"
            _mark_spec_implemented(config, spec_id)
            _step(f"✓ Pipeline abgeschlossen — {report.final_status} · {spec_id} → implemented")
            break

        # Frueher `eval_context or build_output` — die Variable gibt es seit
        # 45b29e6 nicht mehr (F821). Erreichbar ist diese Zeile nur nach einer
        # nicht bestandenen Evaluation, die eval_context immer fuellt.
        error_context = eval_context
        # cleanup happens at the top of the next attempt loop iteration

    # Ensure clean base branch state after all retries
    _git(["checkout", base_branch], config.root)
    _git(["reset", "--hard", "HEAD"], config.root)
    _run(["git", "clean", "-fd"], config.root)

    # Nach allen Retries: bei Fehlschlag Label + Issue
    if report.final_status == "failed":
        if last_pr_url:
            _label_pr(config, last_pr_url, LABEL_FAILED)
        report.issue_url = _open_failure_issue(config, spec_id, last_pr_url, last_eval_context)
        if project_id:
            pr_number = (last_pr_url or spec_id).split("/")[-1]
            record_pr_result(config, project_id, pr_number, passed=False, pass_rate=0.0)

    return report


def _mark_spec_implemented(config: SddConfig, spec_id: str) -> None:
    """Setzt Spec-Status auf implemented nach erfolgreichem Pipeline-Lauf (SPEC-0019/SPEC-0004)."""
    from .frontmatter import patch_status
    from .lifecycle import write_audit_log
    for md in config.specs_dir.rglob("*.md"):
        doc = parse_safe(md)
        if doc and doc.frontmatter.get("id") == spec_id:
            old_status = doc.frontmatter.get("status", "")
            if old_status != "implemented":
                patch_status(md, "implemented")
                write_audit_log(config, spec_id, old_status, "implemented",
                                "orchestrate-pipeline-passed")
            break


def persist_pipeline_report(config: SddConfig, report: PipelineReport) -> Path:
    pipeline_dir = config.sdd_dir / "pipeline"
    pipeline_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d-%H%M%S")
    path = pipeline_dir / f"{ts}-{report.spec_id}.json"
    path.write_text(json.dumps(report.to_dict(), indent=2, ensure_ascii=False),
                    encoding="utf-8")
    return path
