"""SpecFinalizer – einheitliche Finalisierungsphase für alle Implementierungspfade.

Wird verwendet von:
  - sdd finalize (CLI)
  - /sdd-implement (Skill, Schritt 5)
  - sdd orchestrate (nach Code-Generierung)
  - sdd distribute (nach Task-Loop)

Ablauf: git commit → Container-Check → Tests im Container → Container entfernen → PR
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from .config import SddConfig
from .dev_container import (
    DevContainerManager,
    GhFallbackPRStrategy,
    branch_name,
    container_name,
    get_runtime,
    save_test_result,
)

FINALIZE_BRANCH_PREFIX = "feat"


@dataclass
class FinalizeReport:
    spec_id: str
    branch: str
    commit_hash: str | None
    tests_passed: bool
    test_output: str
    pr_url: str | None
    pr_path: Path | None
    error: str | None


def _git(args: list[str], *, cwd: Path, capture: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git"] + args, capture_output=capture, text=True, cwd=cwd)


def _image_exists(cli: str, image: str) -> bool:
    result = subprocess.run(
        [cli, "image", "inspect", image],
        capture_output=True,
    )
    return result.returncode == 0


def _runtime_available(cli: str) -> bool:
    result = subprocess.run([cli, "info"], capture_output=True)
    return result.returncode == 0


class SpecFinalizer:
    def __init__(self, cfg: SddConfig, dry_run: bool = False) -> None:
        self._cfg = cfg
        self._dry_run = dry_run
        self._mgr = DevContainerManager(
            cfg,
            pr_strategy=GhFallbackPRStrategy(),
            runtime=get_runtime(cfg),
        )

    def run(
        self,
        spec_id: str,
        *,
        commit_msg: str = "",
        no_commit: bool = False,
        branch: str | None = None,
        skip_container: bool = False,
    ) -> FinalizeReport:
        effective_branch = branch or branch_name(spec_id, prefix=FINALIZE_BRANCH_PREFIX)
        root = self._cfg.root

        # 1. Branch sicherstellen
        if not no_commit:
            existing = _git(["branch", "--list", effective_branch], cwd=root)
            if effective_branch not in existing.stdout:
                _git(["checkout", "-b", effective_branch], cwd=root)
            else:
                _git(["checkout", effective_branch], cwd=root)

        # 2. Commit (wenn Caller noch nicht committed hat)
        commit_hash: str | None = None
        if not no_commit:
            status = _git(["status", "--porcelain"], cwd=root)
            if status.stdout.strip():
                msg = commit_msg or f"feat({spec_id}): implementiert via sdd finalize"
                _git(["add", "-A"], cwd=root)
                _git(["commit", "-m", msg], cwd=root)
            head = _git(["rev-parse", "HEAD"], cwd=root)
            commit_hash = head.stdout.strip() or None
        else:
            head = _git(["rev-parse", "HEAD"], cwd=root)
            commit_hash = head.stdout.strip() or None

        if self._dry_run:
            return FinalizeReport(
                spec_id=spec_id,
                branch=effective_branch,
                commit_hash=commit_hash,
                tests_passed=True,
                test_output="dry-run: Tests übersprungen",
                pr_url="https://dry-run/pr/1",
                pr_path=None,
                error=None,
            )

        if skip_container:
            pr_url, pr_path, pr_error = self._create_pr(
                spec_id, effective_branch, commit_hash)
            return FinalizeReport(
                spec_id=spec_id,
                branch=effective_branch,
                commit_hash=commit_hash,
                tests_passed=pr_error is None,
                test_output="⚠ Container-Tests wurden übersprungen",
                pr_url=pr_url,
                pr_path=pr_path,
                error=pr_error,
            )

        docker_cfg = self._cfg.raw.get("docker", {})
        compose_file = docker_cfg.get("compose_file", "")
        test_cfg = self._cfg.raw.get("test_runner", {})
        custom_cmd = test_cfg.get("command")
        extra_args = test_cfg.get("extra_args", [])
        timeout = test_cfg.get("timeout_per_spec", 120)

        # Auto-detect project type when no command is configured
        if custom_cmd:
            test_cmd = custom_cmd
            test_args = extra_args
        elif (root / "package.json").exists():
            test_cmd = "npm"
            test_args = ["test"] + extra_args
        else:
            test_cmd = "pytest"
            test_args = ["tests/", "-x", "--tb=short"] + extra_args

        if compose_file:
            # Container-Stack muss bereits laufen
            try:
                test_result = subprocess.run(
                    [test_cmd] + test_args,
                    capture_output=True,
                    text=True,
                    cwd=root,
                    timeout=timeout,
                )
            except FileNotFoundError:
                raise RuntimeError(
                    f"✗ Test-Runner '{test_cmd}' nicht gefunden. "
                    f"Setze 'test_runner.command' in .sdd/config.yaml oder nutze --skip-container."
                )
        else:
            # Container muss bereits laufen
            runtime = get_runtime(self._cfg)
            cname = container_name(spec_id)
            status_now = runtime.inspect_status(cname)
            if status_now != "running":
                raise RuntimeError(
                    f"✗ Dev-Container nicht gefunden – starte ihn mit 'sdd start {spec_id}'"
                )

            inner_cmd = f"cd /workspace && {test_cmd} tests/ -x --tb=short " + " ".join(extra_args)
            test_result = subprocess.run(
                [runtime.cli(), "exec", cname, "bash", "-c", inner_cmd],
                capture_output=True,
                text=True,
                cwd=root,
                timeout=timeout,
            )

        test_output = (test_result.stdout + test_result.stderr).strip()
        tests_passed = test_result.returncode == 0

        passed_count, total_count = _parse_pytest_counts(test_output)
        save_test_result(self._cfg, spec_id, passed=passed_count, total=total_count)

        if not compose_file:
            self._mgr.close(spec_id)

        pr_url: str | None = None
        pr_path: Path | None = None
        error: str | None = None

        if tests_passed:
            # FR-06/CON-0153: Compliance-Kette vor _mark_implemented
            compliance_error = self._run_compliance_check(spec_id)
            if compliance_error:
                return FinalizeReport(
                    spec_id=spec_id,
                    branch=effective_branch,
                    commit_hash=commit_hash,
                    tests_passed=False,
                    test_output=test_output,
                    pr_url=None,
                    pr_path=None,
                    error=compliance_error,
                )
            pr_url, pr_path, pr_error = self._create_pr(
                spec_id, effective_branch, commit_hash)
            if pr_error:
                error = pr_error
                tests_passed = False
        else:
            error = f"Tests fehlgeschlagen im Container:\n{test_output[:1000]}"

        return FinalizeReport(
            spec_id=spec_id,
            branch=effective_branch,
            commit_hash=commit_hash,
            tests_passed=tests_passed,
            test_output=test_output,
            pr_url=pr_url,
            pr_path=pr_path,
            error=error,
        )

    def _run_compliance_check(self, spec_id: str) -> str | None:
        """Gibt None zurück wenn Compliance OK, sonst formatierten Fehlertext."""
        from .compliance import run_compliance_chain
        from .decompose import TaskDecomposer
        from .frontmatter import parse_safe

        spec_doc = None
        for md in self._cfg.specs_dir.rglob("*.md"):
            doc = parse_safe(md)
            if doc and doc.frontmatter.get("id") == spec_id:
                spec_doc = doc
                break
        if spec_doc is None:
            return None

        tasks = TaskDecomposer().load(spec_id, self._cfg)
        issues = run_compliance_chain(
            spec=spec_doc,
            tasks=tasks,
            cfg_raw=self._cfg.raw,
            tests_dir=self._cfg.tests_dir,
            project_root=self._cfg.root,
            strict=True,
        )
        errors = [i for i in issues if i.severity == "error"]
        if not errors:
            return None

        lines = ["✗ Compliance-Gate blockiert finalize:"]
        for issue in errors:
            lines.append(f"  • {issue.message}")
            if issue.hint:
                lines.append(f"    → {issue.hint}")
        return "\n".join(lines)

    def _create_pr(
        self, spec_id: str, branch: str, commit_hash: str | None
    ) -> tuple[str | None, Path | None, str | None]:
        """Erstellt den PR vom finalisierten Branch. Gibt (url, pfad, fehler) zurueck.

        Der Branch wird uebergeben, nicht erneut abgeleitet. Vorher rief diese
        Methode strategy.create(spec_id, cfg) auf, worauf die Strategie sich ihren
        Branch selbst bildete — ueber das dev/-Schema. Committet wurde aber auf
        feat/, sodass der PR die finalisierte Arbeit nicht enthielt.
        """
        guard = self._branch_missing_commit(branch, commit_hash)
        if guard:
            # Kein PR und kein implemented-Status: ein PR ohne die finalisierte
            # Arbeit ist schlimmer als ein Abbruch, weil er beim Merge nichts
            # liefert und die Spec trotzdem Vollzug meldet.
            return None, None, guard

        strategy = GhFallbackPRStrategy()
        pr_url = strategy.create(spec_id, self._cfg, branch=branch)
        pr_path = None if pr_url else self._cfg.root / ".sdd" / "prs" / f"PR-{spec_id}.md"
        self._mark_implemented(spec_id)
        return pr_url, pr_path, None

    def _branch_missing_commit(self, branch: str, commit_hash: str | None) -> str | None:
        """Prueft, ob der PR-Head den Finalize-Commit enthaelt."""
        if not commit_hash:
            return None
        result = _git(
            ["merge-base", "--is-ancestor", commit_hash, branch],
            cwd=self._cfg.root,
        )
        if result.returncode == 0:
            return None
        return (
            f"✗ Branch '{branch}' enthaelt den Finalize-Commit {commit_hash[:12]} nicht — "
            f"kein PR erstellt.\n"
            f"  Ein PR von diesem Branch wuerde die finalisierte Arbeit nicht enthalten.\n"
            f"  Pruefe: git log --oneline {branch} | head"
        )

    def _mark_implemented(self, spec_id: str) -> None:
        from .frontmatter import parse_safe, patch_status
        for md in self._cfg.specs_dir.rglob("*.md"):
            doc = parse_safe(md)
            if doc and doc.frontmatter.get("id") == spec_id:
                patch_status(md, "implemented")
                break


def _parse_pytest_counts(output: str) -> tuple[int, int]:
    """Extrahiert (passed, total) aus pytest-Output. Gibt (0, 0) bei Fehler."""
    import re
    m = re.search(r"(\d+) passed", output)
    passed = int(m.group(1)) if m else 0
    m2 = re.search(r"(\d+) failed", output)
    failed = int(m2.group(1)) if m2 else 0
    return passed, passed + failed
