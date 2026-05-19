"""SpecFinalizer – einheitliche Finalisierungsphase für alle Implementierungspfade.

Wird verwendet von:
  - sdd finalize (CLI)
  - /sdd-implement (Skill, Schritt 5)
  - sdd orchestrate (nach Code-Generierung)
  - sdd distribute (nach Task-Loop)

Ablauf: git commit → Container starten → Tests im Container → Container entfernen → PR
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from .config import SddConfig
from .dev_container import (
    DevContainerManager,
    GhFallbackPRStrategy,
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
    ) -> FinalizeReport:
        runtime = get_runtime(self._cfg)
        cli = runtime.cli()
        if not _runtime_available(cli):
            raise RuntimeError(
                f"'{cli}' ist nicht verfügbar. "
                f"Starte {cli} und führe 'sdd finalize' erneut aus."
            )

        effective_branch = branch or f"{FINALIZE_BRANCH_PREFIX}/{spec_id}"
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

        # 3. Container-Image bauen (wenn nicht vorhanden)
        docker_cfg = self._cfg.raw.get("docker", {})
        image = docker_cfg.get("image", "sdd-dev:latest")
        if not _image_exists(cli, image):
            self._mgr.build()

        # 4. Container starten
        cname = container_name(spec_id)
        status_before = runtime.inspect_status(cname)
        if status_before == "running":
            runtime.stop(cname, check=False)
            runtime.rm(cname, check=False)

        self._mgr.start(spec_id)

        # 5. Tests im Container ausführen (Output capturen)
        test_result = subprocess.run(
            [runtime.cli(), "exec", cname, "bash", "-c",
             "export HOME=/root && cd /workspace && pip install -q -e 'tool/[dev]' && pytest tests/ -x --tb=short -q"],
            capture_output=True,
            text=True,
            cwd=root,
        )
        test_output = (test_result.stdout + test_result.stderr).strip()
        tests_passed = test_result.returncode == 0

        # Parse pass/fail counts für save_test_result
        passed_count, total_count = _parse_pytest_counts(test_output)
        save_test_result(self._cfg, spec_id, passed=passed_count, total=total_count)

        # 6. Container entfernen
        self._mgr.close(spec_id)

        # 7. PR erstellen wenn Tests grün
        pr_url: str | None = None
        pr_path: Path | None = None
        error: str | None = None

        if tests_passed:
            strategy = GhFallbackPRStrategy()
            pr_url = strategy.create(spec_id, self._cfg)
            if pr_url is None:
                pr_path = self._cfg.root / ".sdd" / "prs" / f"PR-{spec_id}.md"
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


def _parse_pytest_counts(output: str) -> tuple[int, int]:
    """Extrahiert (passed, total) aus pytest-Output. Gibt (0, 0) bei Fehler."""
    import re
    m = re.search(r"(\d+) passed", output)
    passed = int(m.group(1)) if m else 0
    m2 = re.search(r"(\d+) failed", output)
    failed = int(m2.group(1)) if m2 else 0
    return passed, passed + failed
