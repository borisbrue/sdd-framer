"""Validierung eines SDD-Projekts.

Prüft drei Ebenen:
1. Frontmatter jeder Datei gegen das passende JSON-Schema
2. Referenzielle Integrität (Spec↔Contract↔Test verweisen aufeinander)
3. Regeln aus config.yaml (z.B. require_contract_per_spec)
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from jsonschema import Draft202012Validator

from .config import SddConfig
from .frontmatter import parse_safe


@dataclass
class Issue:
    """Ein einzelner Validierungs-Fund."""
    severity: str            # "error" | "warning"
    file: Path
    message: str
    instruction: str = ""   # Maschinenlesbare Korrektur-Anweisung für Agenten

    def format(self, root: Path) -> str:
        try:
            rel = self.file.relative_to(root)
        except ValueError:
            rel = self.file
        marker = "✗" if self.severity == "error" else "⚠"
        return f"  {marker} {rel}: {self.message}"

    def to_dict(self, root: Path) -> dict:
        try:
            rel = str(self.file.relative_to(root))
        except ValueError:
            rel = str(self.file)
        return {
            "severity": self.severity,
            "file": rel,
            "message": self.message,
            "instruction": self.instruction,
        }


@dataclass
class Report:
    issues: list[Issue] = field(default_factory=list)

    def add(self, severity: str, file: Path, message: str,
            instruction: str = "") -> None:
        self.issues.append(Issue(severity, file, message, instruction))

    @property
    def errors(self) -> list[Issue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> list[Issue]:
        return [i for i in self.issues if i.severity == "warning"]

    @property
    def ok(self) -> bool:
        return not self.errors


def _load_schema(path: Path) -> Draft202012Validator:
    schema = json.loads(path.read_text(encoding="utf-8"))
    return Draft202012Validator(schema)


def _collect_docs(base: Path) -> list:
    if not base.exists():
        return []
    docs = []
    for md in base.rglob("*.md"):
        if "_archive" in md.parts:
            continue
        d = parse_safe(md)
        if d:
            docs.append(d)
    return docs


def validate(config: SddConfig) -> Report:
    report = Report()
    schemas_dir = config.schemas_dir

    spec_schema = _load_schema(schemas_dir / "spec-frontmatter.schema.json")
    contract_schema = _load_schema(schemas_dir / "contract-frontmatter.schema.json")
    test_schema = _load_schema(schemas_dir / "test-frontmatter.schema.json")

    specs = _collect_docs(config.specs_dir)
    contracts = _collect_docs(config.contracts_dir)
    tests = [d for base in config.all_test_dirs for d in _collect_docs(base)]

    # Index für Referenzprüfung
    spec_index = {d.frontmatter.get("id"): d for d in specs if d.frontmatter.get("id")}
    contract_index = {d.frontmatter.get("id"): d for d in contracts if d.frontmatter.get("id")}
    test_index: dict = {}
    for d in tests:
        tid = d.frontmatter.get("id")
        if not tid:
            continue
        if tid in test_index:
            report.add(
                "error", d.path,
                f"Doppelte Test-ID: {tid} existiert auch in {test_index[tid].path}",
                instruction="Vergib eine eindeutige ID für einen der beiden Tests.",
            )
        else:
            test_index[tid] = d

    # 0) Status-Lifecycle-Prüfung
    allowed_statuses = set(config.raw.get("spec_lifecycle", [
        "draft", "review", "approved", "in-progress", "implemented", "deprecated",
    ]))
    for d in specs:
        status = d.frontmatter.get("status")
        if status and status not in allowed_statuses:
            report.add(
                "warning", d.path,
                f"Unbekannter Spec-Status: '{status}'. Erlaubt: {sorted(allowed_statuses)}",
                instruction=(
                    f"Change status in {d.path.name} to one of: "
                    f"{', '.join(sorted(allowed_statuses))}"
                ),
            )

    # 1) Frontmatter-Schema-Validierung
    for d in specs:
        if not d.frontmatter:
            continue  # README etc. ignorieren
        for err in spec_schema.iter_errors(d.frontmatter):
            report.add("error", d.path, f"Frontmatter ungültig: {err.message}",
                       instruction=f"Fix frontmatter field in {d.path.name}: {err.message}")

    for d in contracts:
        if not d.frontmatter:
            continue
        for err in contract_schema.iter_errors(d.frontmatter):
            report.add("error", d.path, f"Frontmatter ungültig: {err.message}",
                       instruction=f"Fix frontmatter field in {d.path.name}: {err.message}")

    for d in tests:
        if not d.frontmatter:
            continue
        for err in test_schema.iter_errors(d.frontmatter):
            report.add("error", d.path, f"Frontmatter ungültig: {err.message}",
                       instruction=f"Fix frontmatter field in {d.path.name}: {err.message}")

    # 2) Referenzielle Integrität
    # 2a) Specs referenzieren existierende Contracts und Tests
    for spec in specs:
        sid = spec.frontmatter.get("id")
        if not sid:
            continue
        for cid in spec.frontmatter.get("contracts", []) or []:
            if cid not in contract_index:
                report.add(
                    "error", spec.path,
                    f"Spec referenziert nicht existierenden Contract: {cid}",
                    instruction=(
                        f"Create contract file for {cid} in contracts/ "
                        f"or remove {cid} from {sid} contracts list."
                    ),
                )
        for tid in spec.frontmatter.get("tests", []) or []:
            if tid not in test_index:
                report.add(
                    "error", spec.path,
                    f"Spec referenziert nicht existierenden Test: {tid}",
                    instruction=(
                        f"Create test file for {tid} in tests/ "
                        f"or remove {tid} from {sid} tests list."
                    ),
                )
        for dep in spec.frontmatter.get("depends_on", []) or []:
            if dep not in spec_index:
                report.add(
                    "error", spec.path,
                    f"Spec-Abhängigkeit zeigt auf nicht existierende Spec: {dep}",
                    instruction=f"Remove {dep} from {sid} depends_on list or create the spec.",
                )

    # 2b) Contracts referenzieren existierende Specs und Tests
    for c in contracts:
        cid = c.frontmatter.get("id")
        if not cid:
            continue
        ref_spec = c.frontmatter.get("spec")
        if ref_spec and ref_spec not in spec_index:
            report.add(
                "error", c.path,
                f"Contract referenziert nicht existierende Spec: {ref_spec}",
                instruction=f"Set spec: field in {cid} to an existing SPEC-ID.",
            )
        for tid in c.frontmatter.get("tests", []) or []:
            if tid not in test_index:
                report.add(
                    "error", c.path,
                    f"Contract referenziert nicht existierenden Test: {tid}",
                    instruction=(
                        f"Create test file for {tid} or remove {tid} "
                        f"from {cid} tests list."
                    ),
                )
        # Artifact-Datei muss existieren, wenn angegeben – außer der Contract ist abgelöst
        # (SPEC-0058: mit dem Code eines abgelösten Pfads verschwindet auch sein Artefakt).
        artifact = c.frontmatter.get("artifact")
        if artifact and c.frontmatter.get("status") != "deprecated":
            artifact_path = config.root / artifact
            if not artifact_path.exists():
                report.add(
                    "warning", c.path,
                    f"Artifact-Datei fehlt: {artifact}",
                    instruction=f"Create artifact file at {artifact} or clear the artifact field.",
                )

    # 2c) Tests referenzieren existierende Specs und Contracts
    for t in tests:
        ref_spec = t.frontmatter.get("spec")
        ref_contract = t.frontmatter.get("contract")
        tid = t.frontmatter.get("id", t.path.name)
        if ref_spec and ref_spec not in spec_index:
            report.add(
                "error", t.path,
                f"Test referenziert nicht existierende Spec: {ref_spec}",
                instruction=f"Set spec: in {tid} to an existing SPEC-ID.",
            )
        if ref_contract and ref_contract not in contract_index:
            report.add(
                "error", t.path,
                f"Test referenziert nicht existierenden Contract: {ref_contract}",
                instruction=f"Set contract: in {tid} to an existing CON-ID.",
            )

    # 3) Regeln aus config.yaml
    if config.validation_rule("require_contract_per_spec", True):
        for spec in specs:
            sid = spec.frontmatter.get("id")
            if not sid:
                continue
            if spec.frontmatter.get("status") in ("draft", "in-progress"):
                continue
            contracts_ref = spec.frontmatter.get("contracts") or []
            if not contracts_ref:
                report.add(
                    "error", spec.path,
                    "Spec hat keinen Contract (require_contract_per_spec).",
                    instruction=(
                        f"Run `sdd new contract --spec {sid} --format markdown` "
                        f"to create a contract and link it."
                    ),
                )

    if config.validation_rule("require_test_per_contract", True):
        for c in contracts:
            cid = c.frontmatter.get("id")
            if not cid:
                continue
            tests_ref = c.frontmatter.get("tests") or []
            if not tests_ref:
                spec_ref = c.frontmatter.get("spec", "SPEC-XXXX")
                report.add(
                    "error", c.path,
                    "Contract hat keinen Test (require_test_per_contract).",
                    instruction=(
                        f"Run `sdd new test --spec {spec_ref} --contract {cid} "
                        f"--level contract` to create a test stub."
                    ),
                )

    if config.validation_rule("fail_on_orphans", True):
        # Contracts ohne Spec-Referenz
        for c in contracts:
            if not c.frontmatter:
                continue
            cid = c.frontmatter.get("id", c.path.name)
            if not c.frontmatter.get("spec"):
                report.add(
                    "error", c.path,
                    "Contract ohne Spec-Referenz (orphan).",
                    instruction=f"Add spec: <SPEC-ID> field to {cid} frontmatter.",
                )
        # Tests ohne Spec oder Contract
        for t in tests:
            if not t.frontmatter:
                continue
            tid = t.frontmatter.get("id", t.path.name)
            if not t.frontmatter.get("spec") or not t.frontmatter.get("contract"):
                report.add(
                    "error", t.path,
                    "Test ohne Spec/Contract-Referenz (orphan).",
                    instruction=(
                        f"Add spec: <SPEC-ID> and contract: <CON-ID> "
                        f"to {tid} frontmatter."
                    ),
                )

    # 4) AGENTS.md-Vollständigkeit + Taste Invariants (CON-0011)
    if config.validation_rule("check_agents_md", True):
        _check_agents_md(config, report)
        _check_multi_agents_md(config, report)
    if config.validation_rule("check_inline_disables", True):
        _check_inline_disables(config, report)

    # 5) Lifecycle-Regeln (SPEC-0010)
    _check_lifecycle_rules(report, contracts, specs, test_index)

    # 6) FR-Coverage-Compliance (SPEC-0041 FR-07)
    _check_fr_compliance(report, specs, config)

    # 7) Architekturregeln ↔ ADRs (SPEC-0054 FR-06, CON-0197 INV-07/INV-08)
    _check_architecture_links(config, report)

    # 8) Rollendateien der Pipeline (SPEC-0053 FR-01, CON-0199 INV-06)
    _check_roles(config, report)

    return report


def _check_roles(config: SddConfig, report: Report) -> None:
    """Jede `.sdd/roles/<rolle>.md` erfüllt CON-0199 und nennt nur bekannte Rollen-Checks."""
    from .pipeline.roles import RoleError, load_role
    from .pipeline.runner import unknown_checks

    ordner = config.root / ".sdd" / "roles"
    if not ordner.is_dir():
        return
    for datei in sorted(ordner.glob("*.md")):
        try:
            rolle = load_role(config.root, datei.stem)
        except RoleError as exc:
            report.add("error", datei, str(exc),
                       instruction="Frontmatter nach CON-0199 korrigieren (sdd upgrade liefert "
                                   "die Default-Rolle als .md.new).")
            continue
        for check in unknown_checks(rolle):
            report.add("error", datei, f"unbekannter Rollen-Check {check!r}",
                       instruction="Nur registrierte Rollen-Checks verwenden.")


def _check_architecture_links(config: SddConfig, report: Report) -> None:
    from .quality.arch.adr_links import check_adr_links

    adr_dir = str((config.raw.get("adr") or {}).get("output_dir") or "docs/adr")
    for fund in check_adr_links(config.root, adr_dir):
        datei = config.root / fund.path.split(":", 1)[0]
        report.add(fund.level, datei, fund.message,
                   instruction="Regel oder ADR anpassen, sodass adr und enforced_by zueinander passen.")


AGENTS_MD_REQUIRED_SECTIONS = [
    "## Service-Zweck",
    "## Architektur",
    "## Verzeichnisstruktur",
    "## Externe Abhängigkeiten",
    "## Build- und Start-Befehle",
    "## Linting- und Formatierungsregeln",
    "## Taste Invariants",
    "## Konventionen",
    "## SDD-Kontext",
]

# Inline-Suppress-Muster, die Agenten nie verwenden dürfen (Taste Invariant)
_INLINE_DISABLE_PATTERNS = [
    "#" + " noqa",
    "# type:" + " ignore",
    "# pylint:" + " disable",
    "//" + " eslint-disable",
    "/*" + " eslint-disable",
    "@" + "SuppressWarnings",
    "// @ts-" + "ignore",
    "// @ts-" + "nocheck",
    "no" + "lint:",           # Go golangci-lint
]

# Quelldatei-Endungen, die auf Inline-Disables geprüft werden
_SOURCE_EXTENSIONS = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".java", ".kt", ".rb", ".rs",
}


def _check_agents_md(config: SddConfig, report: Report) -> None:
    agents_md = config.root / "AGENTS.md"
    if not agents_md.exists():
        report.add(
            "warning", config.root / "AGENTS.md",
            "AGENTS.md fehlt im Projekt-Root.",
            instruction="Run `sdd init` – der Befehl ist idempotent und legt eine fehlende AGENTS.md nach, ohne Bestehendes zu ueberschreiben.",
        )
        return
    content = agents_md.read_text(encoding="utf-8")
    for section in AGENTS_MD_REQUIRED_SECTIONS:
        if section not in content:
            report.add(
                "warning", agents_md,
                f"AGENTS.md: Pflicht-Sektion fehlt: {section!r}",
                instruction=f"Add section '{section}' to AGENTS.md with meaningful content.",
            )
            continue
        # Sektion vorhanden — prüfe ob nur Placeholder-Inhalt
        idx = content.find(section)
        after = content[idx + len(section):]
        next_h2 = after.find("\n## ")
        section_body = after[:next_h2] if next_h2 != -1 else after
        stripped = section_body.strip()
        # Nur Kommentare oder leer → Warnung
        if not stripped or all(
            line.strip().startswith("<!--") or line.strip() == ""
            for line in stripped.splitlines()
        ):
            report.add(
                "warning", agents_md,
                f"AGENTS.md: Sektion {section!r} enthält nur Platzhalter.",
                instruction=(
                    f"Replace the placeholder in section '{section}' in AGENTS.md "
                    f"with actual content describing this aspect of your service."
                ),
            )

    # Taste Invariant: Inline-Disable-Verbot in AGENTS.md explizit dokumentiert?
    if "## Taste Invariants" in content:
        taste_idx = content.find("## Taste Invariants")
        taste_after = content[taste_idx:]
        next_h2 = taste_after.find("\n## ", 4)
        taste_body = taste_after[:next_h2] if next_h2 != -1 else taste_after
        if not any(pat.lower() in taste_body.lower() for pat in
                   ["inline", "disable", "noqa", "suppress"]):
            report.add(
                "warning", agents_md,
                "AGENTS.md Taste Invariants: Inline-Disable-Verbot nicht dokumentiert.",
                instruction=(
                    "Add a rule to '## Taste Invariants' that explicitly forbids "
                    "inline suppression comments (noqa, eslint-disable, @" + "SuppressWarnings, etc.)."
                ),
            )


def _check_multi_agents_md(config: SddConfig, report: Report) -> None:
    """Warnt wenn Unterverzeichnisse mit Quellcode kein eigenes AGENTS.md haben."""
    skip_dirs = {".git", "__pycache__", "node_modules", ".venv", "venv",
                 ".sdd", "dist", "build", ".mypy_cache", ".pytest_cache"}
    # Indikatoren für ein "signifikantes" Subkomponenten-Verzeichnis
    source_indicators = {"src", "lib", "app", "cmd", "pkg", "source", "main"}
    for subdir in sorted(config.root.iterdir()):
        if not subdir.is_dir():
            continue
        if subdir.name.startswith(".") or subdir.name in skip_dirs:
            continue
        has_source = any((subdir / ind).is_dir() for ind in source_indicators)
        if not has_source:
            continue
        agents_md = subdir / "AGENTS.md"
        if not agents_md.exists():
            report.add(
                "warning", agents_md,
                f"Unterverzeichnis '{subdir.name}/' enthält Quellcode aber kein AGENTS.md.",
                instruction=(
                    # `sdd init` legt nur die AGENTS.md im Projekt-Root an; fuer
                    # Unterverzeichnisse gibt es kein Kommando. Der frueher hier
                    # genannte `sdd new agents-md --subdir` ist entfernt und
                    # endet mit exit 1.
                    f"Kopiere .sdd/templates/agents-md/default.md nach "
                    f"{subdir.name}/AGENTS.md und fuelle die Sektionen aus."
                ),
            )


def _check_inline_disables(config: SddConfig, report: Report) -> None:
    """Findet Inline-Suppress-Kommentare in Quelldateien (Taste Invariant)."""
    skip_dirs = {".git", "__pycache__", "node_modules", ".venv", "venv",
                 ".sdd", "dist", "build", ".mypy_cache"}
    for src_file in config.root.rglob("*"):
        if not src_file.is_file():
            continue
        if src_file.suffix not in _SOURCE_EXTENSIONS:
            continue
        if any(part in skip_dirs for part in src_file.parts):
            continue
        try:
            text = src_file.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            for pat in _INLINE_DISABLE_PATTERNS:
                if pat in line:
                    rel = src_file.relative_to(config.root)
                    report.add(
                        "error", src_file,
                        f"Taste Invariant verletzt: Inline-Suppress in {rel}:{lineno} "
                        f"({pat!r}). Agenten dürfen Linter-Fehler nicht unterdrücken.",
                        instruction=(
                            f"Fix the underlying issue at {rel}:{lineno} instead of "
                            f"suppressing it with {pat!r}."
                        ),
                    )
                    break  # nur ein Treffer pro Zeile


def _check_lifecycle_rules(
    report: Report,
    contracts: list,
    specs: list,
    test_index: dict,
) -> None:
    """SPEC-0010 Lifecycle-Validierungsregeln FR-10 und FR-11."""
    # Hilfsindex: Contract-ID → Contract-Doc
    contract_by_id: dict = {
        c.frontmatter.get("id"): c
        for c in contracts
        if c.frontmatter.get("id")
    }

    # FR-10: Contract mit status=review und ohne verknüpften Test → ERROR
    for c in contracts:
        cid = c.frontmatter.get("id")
        if not cid:
            continue
        if c.frontmatter.get("status") != "review":
            continue
        tests_ref = c.frontmatter.get("tests") or []
        if not tests_ref:
            report.add(
                "error", c.path,
                f"{cid} hat Status 'review' aber keinen verknüpften Test (FR-10).",
                instruction=(
                    f"Run `sdd review-contract {cid}` to auto-generate a test, "
                    f"or `sdd new test --spec <SPEC> --contract {cid} --level contract`."
                ),
            )

    # FR-11: Spec mit status=approved aber mindestens ein Contract mit status=review → WARNING
    for spec in specs:
        sid = spec.frontmatter.get("id")
        if not sid:
            continue
        if spec.frontmatter.get("status") != "approved":
            continue
        for cid in spec.frontmatter.get("contracts", []) or []:
            c = contract_by_id.get(cid)
            if c and c.frontmatter.get("status") == "review":
                report.add(
                    "warning", spec.path,
                    f"{sid} hat Status 'approved' aber {cid} ist noch in 'review' (FR-11).",
                    instruction=(
                        f"Review and approve {cid} or update {sid} status to 'review'."
                    ),
                )


def _check_fr_compliance(report: Report, specs: list, config: SddConfig) -> None:
    """FR-07: Compliance-Kette für approved/in-progress Specs (SPEC-0041)."""
    from .compliance import run_compliance_chain
    from .decompose import TaskDecomposer

    target_statuses = {"approved", "in-progress"}
    decomposer = TaskDecomposer()

    for spec in specs:
        status = spec.frontmatter.get("status")
        if status not in target_statuses:
            continue
        tasks = decomposer.load(spec.frontmatter.get("id", ""), config)
        issues = run_compliance_chain(
            spec=spec,
            tasks=tasks,
            cfg_raw=config.raw,
            tests_dir=config.tests_dir,
            project_root=config.root,
        )
        for issue in issues:
            # Warnungen wurden hier bisher verworfen. Die Kette meldet im
            # Berichtsmodus (strict=False) genau ueber diesen Weg, etwa offene
            # Tasks — stillschweigend zu schlucken hiesse, die Pruefung zu
            # haben und ihr Ergebnis nicht zu zeigen.
            if issue.severity in ("error", "warning"):
                report.add(
                    issue.severity,
                    spec.path,
                    issue.message,
                    instruction=issue.hint,
                )
