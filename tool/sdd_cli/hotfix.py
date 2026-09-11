"""Hotfix Flow – schlanker Bugfix-Zyklus ohne SDD-Overhead (SPEC-0031)."""
from __future__ import annotations

import datetime
import subprocess
from pathlib import Path


def _hotfixes_dir(repo_root: Path) -> Path:
    return repo_root / ".sdd" / "hotfixes"


def _next_hf_id(repo_root: Path) -> str:
    d = _hotfixes_dir(repo_root)
    d.mkdir(parents=True, exist_ok=True)
    existing = [
        p.stem for p in d.glob("HF-*.md")
        if p.stem.startswith("HF-") and p.stem[3:].isdigit()
    ]
    if not existing:
        return "HF-0001"
    last = max(int(s[3:]) for s in existing)
    return f"HF-{last + 1:04d}"


def _hf_path(repo_root: Path, hf_id: str) -> Path:
    return _hotfixes_dir(repo_root) / f"{hf_id}.md"


def _record_loader():
    """YAML-Loader, der Skalare als Text belässt; nur `null` wird aufgelöst.

    Ein Record ist eine Handvoll Textfelder. yaml.safe_load riet aber den Typ:
    Ein Kurzhash aus lauter Ziffern (`commit: 2494608`, jeder 16.) wurde int,
    und `sdd status` brach beim Rendern ab (#130). Schlimmer: `0123456` wurde
    als Oktalzahl zu 42798, str() hätte einen falschen Hash geliefert. Und ein
    unquotiertes `created: 2026-09-11` wurde ein date. Der Writer quotet solche
    Werte, aber die Dateien sind von Hand editierbar.
    """
    import yaml

    class RecordLoader(yaml.SafeLoader):
        pass

    null = "tag:yaml.org,2002:null"
    # Kopie statt Änderung: das dict gehört sonst SafeLoader selbst.
    RecordLoader.yaml_implicit_resolvers = {
        k: [(tag, rx) for tag, rx in v if tag == null]
        for k, v in yaml.SafeLoader.yaml_implicit_resolvers.items()
    }
    return RecordLoader


def _read_hf(path: Path) -> dict:
    import re

    import yaml
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n?", text, re.DOTALL)
    if m:
        return yaml.load(m.group(1), Loader=_record_loader()) or {}
    return {}


def _write_hf(path: Path, data: dict) -> None:
    import yaml
    yaml_text = yaml.safe_dump(data, sort_keys=False, allow_unicode=True).rstrip("\n")
    path.write_text(f"---\n{yaml_text}\n---\n", encoding="utf-8")


def _now_date() -> str:
    return datetime.date.today().isoformat()


def _git(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["git"] + args, capture_output=True, text=True, cwd=cwd)


def _append_audit(repo_root: Path, line: str) -> None:
    audit = repo_root / ".sdd" / "audit.log"
    with audit.open("a", encoding="utf-8") as f:
        ts = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        f.write(f"{ts}  {line}\n")


def start(repo_root: Path, description: str) -> str:
    """Create a new hotfix record. Returns the new HF-ID."""
    hf_id = _next_hf_id(repo_root)
    data = {
        "id": hf_id,
        "description": description,
        "status": "open",
        "created": _now_date(),
        "commit": None,
    }
    _write_hf(_hf_path(repo_root, hf_id), data)
    _append_audit(repo_root, f"hotfix.start  {hf_id}  {description!r}")
    return hf_id


def finalize(repo_root: Path, hf_id: str) -> str:
    """Run tests, commit staged changes, update record. Returns commit hash."""
    path = _hf_path(repo_root, hf_id)
    if not path.exists():
        raise FileNotFoundError(f"Hotfix-Record nicht gefunden: {hf_id}")

    data = _read_hf(path)
    if data.get("status") != "open":
        raise ValueError(f"{hf_id} hat Status '{data.get('status')}' – nur 'open' kann finalisiert werden.")

    test_proc = subprocess.run(
        ["uv", "run", "pytest", "tests/", "-x", "--tb=short", "-q"],
        capture_output=True,
        text=True,
        cwd=repo_root,
    )
    if test_proc.returncode != 0:
        output = (test_proc.stdout + test_proc.stderr).strip()
        raise RuntimeError(
            f"Tests fehlgeschlagen – Hotfix anpassen vor Commit:\n{output[:800]}"
        )

    description = data.get("description", hf_id)
    proc = _git(
        ["commit", "-m", f"hotfix: {description} ({hf_id})"],
        cwd=repo_root,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "git commit fehlgeschlagen")

    commit_hash = _git(["rev-parse", "--short", "HEAD"], cwd=repo_root).stdout.strip()
    data["status"] = "done"
    data["commit"] = commit_hash
    _write_hf(path, data)
    _append_audit(repo_root, f"hotfix.finalize  {hf_id}  commit={commit_hash}")
    return commit_hash


def abort(repo_root: Path, hf_id: str) -> None:
    """Mark hotfix as aborted without committing."""
    path = _hf_path(repo_root, hf_id)
    if not path.exists():
        raise FileNotFoundError(f"Hotfix-Record nicht gefunden: {hf_id}")
    data = _read_hf(path)
    data["status"] = "aborted"
    _write_hf(path, data)
    _append_audit(repo_root, f"hotfix.abort  {hf_id}")


def list_hotfixes(repo_root: Path, status_filter: str | None = None) -> list[dict]:
    """Return all hotfix records, optionally filtered by status."""
    d = _hotfixes_dir(repo_root)
    if not d.exists():
        return []
    result = []
    for p in sorted(d.glob("HF-*.md")):
        data = _read_hf(p)
        if data.get("id") and (status_filter is None or data.get("status") == status_filter):
            result.append(data)
    return result
