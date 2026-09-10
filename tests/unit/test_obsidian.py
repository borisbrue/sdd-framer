"""Unit- und Acceptance-Tests für SPEC-0009 – Obsidian Vault Synchronisation."""
from __future__ import annotations

import sys
import time
from datetime import date, timedelta
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tool"))

from sdd_cli.config import SddConfig
from sdd_cli.obsidian import (
    CONFLICTS_FILE,
    WARNINGS_LOG,
    export,
    ids_to_wiki_links,
    import_vault,
    obsidian_config,
    wiki_links_to_ids,
)

# ─── Helpers ──────────────────────────────────────────────────────────────────

def _make_cfg(root: Path, extra_raw: dict | None = None) -> SddConfig:
    raw = extra_raw or {}
    return SddConfig(root=root, raw=raw)


def _write_spec(root: Path, spec_id: str, slug: str, body: str = "",
                updated: str | None = None) -> Path:
    specs = root / ".sdd" / "specs"
    specs.mkdir(parents=True, exist_ok=True)
    fm: dict = {"id": spec_id, "title": slug, "status": "draft"}
    if updated:
        fm["updated"] = updated
    fm_text = yaml.safe_dump(fm, sort_keys=False, allow_unicode=True).rstrip("\n")
    p = specs / f"{spec_id}-{slug}.md"
    p.write_text(f"---\n{fm_text}\n---\n{body}", encoding="utf-8")
    return p


def _write_vault_spec(vault_root: Path, subfolder: str, spec_id: str, slug: str,
                      body: str = "", updated: str | None = None) -> Path:
    sdd = vault_root / subfolder / "specs"
    sdd.mkdir(parents=True, exist_ok=True)
    fm: dict = {"id": spec_id, "title": slug, "status": "draft"}
    if updated:
        fm["updated"] = updated
    fm_text = yaml.safe_dump(fm, sort_keys=False, allow_unicode=True).rstrip("\n")
    p = sdd / f"{spec_id}-{slug}.md"
    p.write_text(f"---\n{fm_text}\n---\n{body}", encoding="utf-8")
    return p


# ─── TST-0043: Wiki-Link-Konvertierung ────────────────────────────────────────

class TestWikiLinks:
    def test_id_to_wiki_link_known(self):
        """CON-0001 mit bekanntem Slug → [[CON-0001-login]]"""
        slug_map = {"CON-0001": "CON-0001-login"}
        result = ids_to_wiki_links("Siehe CON-0001 für Details.", slug_map)
        assert "[[CON-0001-login]]" in result
        assert "CON-0001 für" not in result

    def test_multiple_ids_converted(self):
        """Mehrere IDs im selben Body werden alle konvertiert."""
        slug_map = {
            "SPEC-0001": "SPEC-0001-user-login",
            "CON-0001": "CON-0001-login",
        }
        result = ids_to_wiki_links("SPEC-0001 referenziert CON-0001.", slug_map)
        assert "[[SPEC-0001-user-login]]" in result
        assert "[[CON-0001-login]]" in result

    def test_unknown_id_stays_raw(self):
        """Unbekannte ID (kein Slug in map) bleibt unverändert."""
        result = ids_to_wiki_links("Siehe CON-9999.", {})
        assert "CON-9999" in result
        assert "[[" not in result

    def test_no_ids_in_body(self):
        """Body ohne IDs bleibt unverändert."""
        body = "Keine IDs hier."
        assert ids_to_wiki_links(body, {"SPEC-0001": "SPEC-0001-x"}) == body

    def test_wiki_link_to_id(self):
        """[[CON-0001-login]] → CON-0001"""
        result = wiki_links_to_ids("Siehe [[CON-0001-login]] für Details.")
        assert "CON-0001" in result
        assert "[[" not in result

    def test_multiple_wiki_links_to_ids(self):
        """Mehrere Wiki-Links werden alle konvertiert."""
        body = "[[SPEC-0001-user-login]] referenziert [[CON-0001-login]]."
        result = wiki_links_to_ids(body)
        assert "SPEC-0001" in result
        assert "CON-0001" in result
        assert "[[" not in result

    def test_auto_wiki_links_false_no_conversion(self, tmp_path):
        """auto_wiki_links=false: keine Wiki-Links beim Export."""
        root = tmp_path / "project"
        vault = tmp_path / "vault"
        vault.mkdir()
        _write_spec(root, "SPEC-0001", "user-login", body="Referenz: CON-0001")
        raw = {"obsidian": {"vault_path": str(vault), "auto_wiki_links": False}}
        cfg = _make_cfg(root, raw)
        # config.yaml schreiben
        (root / ".sdd").mkdir(parents=True, exist_ok=True)
        (root / ".sdd" / "config.yaml").write_text("", encoding="utf-8")

        result = export(cfg, dry_run=False)
        assert result.written
        exported = (vault / "SDD" / "specs" / "SPEC-0001-user-login.md").read_text()
        assert "CON-0001" in exported
        assert "[[" not in exported

    def test_repeated_id_all_occurrences_converted(self):
        """Dieselbe ID mehrfach im Body → alle Vorkommen werden konvertiert."""
        slug_map = {"CON-0001": "CON-0001-login"}
        body = "CON-0001 ist gut. Auch CON-0001 ist wichtig."
        result = ids_to_wiki_links(body, slug_map)
        assert result.count("[[CON-0001-login]]") == 2


# ─── TST-0044: Conflict-Erkennung ────────────────────────────────────────────

class TestConflictDetection:
    def _setup(self, tmp_path: Path):
        root = tmp_path / "project"
        vault = tmp_path / "vault"
        vault.mkdir()
        (root / ".sdd").mkdir(parents=True, exist_ok=True)
        (root / ".sdd" / "config.yaml").write_text("", encoding="utf-8")

        str(date.today())
        yesterday = str(date.today() - timedelta(days=1))

        # Spec im Projekt erstellen
        spec_path = _write_spec(root, "SPEC-0001", "user-login", updated=yesterday)

        raw = {"obsidian": {"vault_path": str(vault)}}
        cfg = _make_cfg(root, raw)

        # Exportieren (Stempel setzen)
        export(cfg)

        return root, vault, cfg, spec_path

    def test_no_conflict_when_only_vault_changed(self, tmp_path):
        """Nur Vault geändert → kein Conflict, Datei wird importiert."""
        root, vault, cfg, spec_path = self._setup(tmp_path)

        # Vault-Datei bearbeiten (mtime aktualisieren)
        vault_file = vault / "SDD" / "specs" / "SPEC-0001-user-login.md"
        vault_file.write_text(vault_file.read_text() + "\n<!-- Vault-Edit -->", encoding="utf-8")

        result = import_vault(cfg)
        assert len(result.conflicts) == 0
        assert len(result.imported) > 0

    def test_conflict_when_both_changed(self, tmp_path):
        """Beide Seiten geändert → Conflict erkannt."""
        root, vault, cfg, spec_path = self._setup(tmp_path)

        # Beide Seiten NACH dem Export-Stempel modifizieren
        time.sleep(0.05)
        vault_file = vault / "SDD" / "specs" / "SPEC-0001-user-login.md"
        vault_file.write_text(vault_file.read_text() + "\n<!-- Vault-Edit -->", encoding="utf-8")
        spec_path.write_text(spec_path.read_text() + "\n<!-- Projekt-Edit -->", encoding="utf-8")

        result = import_vault(cfg)
        assert "SPEC-0001" in result.conflicts

    def test_conflict_does_not_overwrite(self, tmp_path):
        """Bei Conflict wird Projekt-Datei nicht überschrieben."""
        root, vault, cfg, spec_path = self._setup(tmp_path)

        time.sleep(0.05)
        original_content = spec_path.read_text()
        vault_file = vault / "SDD" / "specs" / "SPEC-0001-user-login.md"
        vault_file.write_text(vault_file.read_text() + "\n<!-- Vault-Edit -->", encoding="utf-8")
        spec_path.write_text(original_content + "\n<!-- Projekt-Edit -->", encoding="utf-8")

        import_vault(cfg)
        assert spec_path.read_text() == original_content + "\n<!-- Projekt-Edit -->"

    def test_conflict_recorded_in_yaml(self, tmp_path):
        """Conflict-Eintrag enthält Pflichtfelder."""
        root, vault, cfg, spec_path = self._setup(tmp_path)

        time.sleep(0.05)
        vault_file = vault / "SDD" / "specs" / "SPEC-0001-user-login.md"
        vault_file.write_text(vault_file.read_text() + "\n<!-- V -->", encoding="utf-8")
        spec_path.write_text(spec_path.read_text() + "\n<!-- P -->", encoding="utf-8")

        import_vault(cfg)

        conflicts_file = root / CONFLICTS_FILE
        assert conflicts_file.exists()
        data = yaml.safe_load(conflicts_file.read_text()) or []
        assert len(data) >= 1
        entry = data[0]
        for key in ("id", "vault_path", "project_path", "detected_at"):
            assert key in entry, f"Pflichtfeld '{key}' fehlt"
        assert entry["id"] == "SPEC-0001"

    def test_no_conflict_without_stamp(self, tmp_path):
        """Kein Exportstempel → kein Conflict (frischer Import)."""
        root = tmp_path / "project"
        vault = tmp_path / "vault"
        vault.mkdir()
        (root / ".sdd").mkdir(parents=True, exist_ok=True)
        (root / ".sdd" / "config.yaml").write_text("", encoding="utf-8")

        _write_spec(root, "SPEC-0001", "user-login")
        _write_vault_spec(vault, "SDD", "SPEC-0001", "user-login",
                          body="# Vault-Version")

        raw = {"obsidian": {"vault_path": str(vault)}}
        cfg = _make_cfg(root, raw)

        result = import_vault(cfg)
        assert len(result.conflicts) == 0


# ─── TST-0045: Import-Filterung und Path-Traversal ────────────────────────────

class TestImportFiltering:
    def _setup(self, tmp_path: Path):
        root = tmp_path / "project"
        vault = tmp_path / "vault"
        vault.mkdir()
        (root / ".sdd").mkdir(parents=True, exist_ok=True)
        (root / ".sdd" / "config.yaml").write_text("", encoding="utf-8")
        raw = {"obsidian": {"vault_path": str(vault)}}
        return root, vault, _make_cfg(root, raw)

    def _write_vault_raw(self, vault: Path, subfolder: str, filename: str,
                         content: str) -> Path:
        p = vault / subfolder / "specs" / filename
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return p

    def test_unknown_id_pattern_skipped(self, tmp_path):
        """Datei mit UNKNOWN-9999 → übersprungen."""
        root, vault, cfg = self._setup(tmp_path)
        self._write_vault_raw(vault, "SDD", "UNKNOWN-9999-test.md",
                              "---\nid: UNKNOWN-9999\ntitle: test\n---\nBody\n")
        result = import_vault(cfg)
        assert any("UNKNOWN-9999" in w for w in result.warnings)
        assert len(result.imported) == 0

    def test_invalid_yaml_frontmatter_skipped(self, tmp_path):
        """Ungültiges YAML-Frontmatter → übersprungen, Warnung."""
        root, vault, cfg = self._setup(tmp_path)
        self._write_vault_raw(vault, "SDD", "SPEC-0001-test.md",
                              "---\n: ungültig: yaml: [{\n---\nBody\n")
        result = import_vault(cfg)
        # Datei wird übersprungen (parse_safe gibt None zurück)
        assert len(result.imported) == 0

    def test_id_mismatch_with_filename_skipped(self, tmp_path):
        """id: SPEC-0002 aber Dateiname SPEC-0001-test.md → übersprungen."""
        root, vault, cfg = self._setup(tmp_path)
        self._write_vault_raw(vault, "SDD", "SPEC-0001-test.md",
                              "---\nid: SPEC-0002\ntitle: test\n---\nBody\n")
        result = import_vault(cfg)
        assert any("SPEC-0001" in w or "SPEC-0002" in w for w in result.warnings)
        assert len(result.imported) == 0

    def test_valid_spec_id_imported(self, tmp_path):
        """Gültige SPEC-ID → wird importiert."""
        root, vault, cfg = self._setup(tmp_path)
        _write_spec(root, "SPEC-0001", "user-login")
        _write_vault_spec(vault, "SDD", "SPEC-0001", "user-login", body="Vault-Inhalt")
        result = import_vault(cfg)
        assert len(result.imported) > 0

    def test_valid_con_id_imported(self, tmp_path):
        """Gültige CON-ID → wird importiert."""
        root, vault, cfg = self._setup(tmp_path)
        contracts = root / ".sdd" / "contracts" / "behavior"
        contracts.mkdir(parents=True)
        fm_text = "id: CON-0001\ntitle: login\nstatus: draft"
        (contracts / "CON-0001-login.md").write_text(
            f"---\n{fm_text}\n---\nBody\n", encoding="utf-8"
        )
        # Vault-Seite
        vault_con = vault / "SDD" / "contracts"
        vault_con.mkdir(parents=True)
        (vault_con / "CON-0001-login.md").write_text(
            f"---\n{fm_text}\n---\nVault-Body\n", encoding="utf-8"
        )
        result = import_vault(cfg)
        assert any("CON-0001" in p for p in result.imported)

    def test_adr_id_imported(self, tmp_path):
        """Gültige ADR-ID → wird importiert."""
        root, vault, cfg = self._setup(tmp_path)
        adr_dir = root / "docs" / "adr"
        adr_dir.mkdir(parents=True)
        fm_text = "id: ADR-0001\ntitle: test-adr\nstatus: draft"
        (adr_dir / "ADR-0001-test-adr.md").write_text(
            f"---\n{fm_text}\n---\nBody\n", encoding="utf-8"
        )
        vault_adr = vault / "SDD" / "adrs"
        vault_adr.mkdir(parents=True)
        (vault_adr / "ADR-0001-test-adr.md").write_text(
            f"---\n{fm_text}\n---\nVault-ADR\n", encoding="utf-8"
        )
        result = import_vault(cfg)
        assert any("ADR-0001" in p for p in result.imported)

    def test_warnings_logged_to_file(self, tmp_path):
        """Warnungen werden in obsidian-warnings.log geschrieben."""
        root, vault, cfg = self._setup(tmp_path)
        self._write_vault_raw(vault, "SDD", "UNKNOWN-9999-x.md",
                              "---\nid: UNKNOWN-9999\n---\nBody\n")
        import_vault(cfg)
        log = root / WARNINGS_LOG
        assert log.exists()
        assert "UNKNOWN-9999" in log.read_text()


# ─── TST-0046: Idempotenz und Config ─────────────────────────────────────────

class TestIdempotenzAndConfig:
    def test_second_export_identical_files(self, tmp_path):
        """Zweiter Export ohne Änderungen → byte-gleiche Dateien."""
        root = tmp_path / "project"
        vault = tmp_path / "vault"
        vault.mkdir()
        (root / ".sdd").mkdir(parents=True, exist_ok=True)
        (root / ".sdd" / "config.yaml").write_text("", encoding="utf-8")

        _write_spec(root, "SPEC-0001", "user-login",
                    body="Login-Feature", updated="2026-05-14")
        raw = {"obsidian": {"vault_path": str(vault)}}
        cfg = _make_cfg(root, raw)

        export(cfg)
        first_content = (vault / "SDD" / "specs" / "SPEC-0001-user-login.md").read_bytes()

        export(cfg)
        second_content = (vault / "SDD" / "specs" / "SPEC-0001-user-login.md").read_bytes()

        assert first_content == second_content

    def test_vault_as_subdir_of_project_raises(self, tmp_path):
        """vault_path als Unterverzeichnis des Projekts → ValueError."""
        root = tmp_path / "project"
        (root / ".sdd").mkdir(parents=True, exist_ok=True)
        (root / ".sdd" / "config.yaml").write_text("", encoding="utf-8")
        vault = root / "vault-subdir"
        vault.mkdir()

        raw = {"obsidian": {"vault_path": str(vault)}}
        cfg = _make_cfg(root, raw)

        with pytest.raises(ValueError, match="Cycle-Prevention"):
            export(cfg)

    def test_watch_interval_less_than_one_raises(self, tmp_path):
        """watch_interval_secs: 0 → ValueError."""
        root = tmp_path / "project"
        (root / ".sdd").mkdir(parents=True, exist_ok=True)
        (root / ".sdd" / "config.yaml").write_text("", encoding="utf-8")
        raw = {"obsidian": {"vault_path": "/tmp/vault", "watch_interval_secs": 0}}
        cfg = _make_cfg(root, raw)

        with pytest.raises(ValueError, match="watch_interval_secs"):
            obsidian_config(cfg)

    def test_missing_vault_path_raises(self, tmp_path):
        """Kein vault_path und kein Override → ValueError."""
        root = tmp_path / "project"
        (root / ".sdd").mkdir(parents=True, exist_ok=True)
        (root / ".sdd" / "config.yaml").write_text("", encoding="utf-8")
        cfg = _make_cfg(root, {})

        with pytest.raises(ValueError, match="vault_path nicht konfiguriert"):
            export(cfg)

    def test_defaults_when_obsidian_section_missing(self, tmp_path):
        """Fehlende obsidian-Sektion → Defaults: subfolder=SDD, interval=5, auto_links=True."""
        root = tmp_path / "project"
        cfg = _make_cfg(root, {})
        ocfg = obsidian_config(cfg)
        assert ocfg.subfolder == "SDD"
        assert ocfg.watch_interval_secs == 5
        assert ocfg.auto_wiki_links is True
        assert ocfg.vault_path is None

    def test_dry_run_writes_no_files(self, tmp_path):
        """--dry-run schreibt keine Dateien in den Vault."""
        root = tmp_path / "project"
        vault = tmp_path / "vault"
        vault.mkdir()
        (root / ".sdd").mkdir(parents=True, exist_ok=True)
        (root / ".sdd" / "config.yaml").write_text("", encoding="utf-8")
        _write_spec(root, "SPEC-0001", "user-login")
        raw = {"obsidian": {"vault_path": str(vault)}}
        cfg = _make_cfg(root, raw)

        result = export(cfg, dry_run=True)
        assert len(result.written) > 0  # Aktionen gemeldet
        assert not (vault / "SDD" / "specs" / "SPEC-0001-user-login.md").exists()


# ─── TST-0047: Acceptance ─────────────────────────────────────────────────────

class TestAcceptance:
    def _full_project(self, tmp_path: Path):
        root = tmp_path / "project"
        vault = tmp_path / "vault"
        vault.mkdir()
        (root / ".sdd").mkdir(parents=True, exist_ok=True)
        (root / ".sdd" / "config.yaml").write_text("", encoding="utf-8")
        _write_spec(root, "SPEC-0001", "user-login",
                    body="Referenz: CON-0001", updated="2026-05-01")
        contracts = root / ".sdd" / "contracts" / "behavior"
        contracts.mkdir(parents=True)
        fm_text = "id: CON-0001\ntitle: login\nstatus: draft\nupdated: '2026-05-01'"
        (contracts / "CON-0001-login.md").write_text(
            f"---\n{fm_text}\n---\nLogin-Verhalten\n", encoding="utf-8"
        )
        raw = {"obsidian": {"vault_path": str(vault)}}
        cfg = _make_cfg(root, raw)
        return root, vault, cfg

    def test_export_creates_sdd_structure(self, tmp_path):
        """Export legt SDD/specs/ und SDD/contracts/ an."""
        root, vault, cfg = self._full_project(tmp_path)
        export(cfg)
        assert (vault / "SDD" / "specs" / "SPEC-0001-user-login.md").exists()
        assert (vault / "SDD" / "contracts" / "CON-0001-login.md").exists()

    def test_export_creates_index(self, tmp_path):
        """Export erzeugt SDD/index.md mit Wiki-Links."""
        root, vault, cfg = self._full_project(tmp_path)
        export(cfg)
        index = vault / "SDD" / "index.md"
        assert index.exists()
        content = index.read_text()
        assert "SPEC-0001-user-login" in content
        assert "CON-0001-login" in content

    def test_import_after_vault_edit_no_conflict(self, tmp_path):
        """Import nach Vault-Edit (Projekt unverändert) → kein Conflict."""
        root, vault, cfg = self._full_project(tmp_path)
        export(cfg)

        vault_spec = vault / "SDD" / "specs" / "SPEC-0001-user-login.md"
        vault_spec.write_text(vault_spec.read_text() + "\n# Vault-Ergänzung",
                              encoding="utf-8")

        result = import_vault(cfg)
        assert len(result.conflicts) == 0
        assert len(result.imported) > 0

    def test_import_conflict_on_both_changed(self, tmp_path):
        """Beide Seiten geändert → Conflict, kein Überschreiben, Exit-relevanter Rückgabewert."""
        root, vault, cfg = self._full_project(tmp_path)
        export(cfg)

        spec_path = root / ".sdd" / "specs" / "SPEC-0001-user-login.md"
        vault_spec = vault / "SDD" / "specs" / "SPEC-0001-user-login.md"

        time.sleep(0.05)
        spec_path.write_text(spec_path.read_text() + "\n# Projekt-Änderung",
                             encoding="utf-8")
        vault_spec.write_text(vault_spec.read_text() + "\n# Vault-Änderung",
                              encoding="utf-8")

        result = import_vault(cfg)
        assert "SPEC-0001" in result.conflicts
        conflicts_file = root / CONFLICTS_FILE
        assert conflicts_file.exists()

    def test_missing_vault_config_error(self, tmp_path):
        """Kein vault_path → ValueError mit passendem Text."""
        root = tmp_path / "project"
        (root / ".sdd").mkdir(parents=True, exist_ok=True)
        (root / ".sdd" / "config.yaml").write_text("", encoding="utf-8")
        cfg = _make_cfg(root, {})

        with pytest.raises(ValueError, match="vault_path nicht konfiguriert"):
            export(cfg)
