# TST-0179 – TypeAwareTestChecker + RouteRegistrationChecker — Tag-basierte Pflichtprüfung
# Spec: SPEC-0041 | Contract: CON-0154
from pathlib import Path

from sdd_cli.compliance import RouteRegistrationChecker, TypeAwareTestChecker
from sdd_cli.frontmatter import Document


def _spec(tags: list[str], tests: list[str] | None = None) -> Document:
    return Document(
        path=Path("fake.md"),
        frontmatter={"id": "SPEC-TEST", "status": "approved", "tags": tags, "tests": tests or []},
        body="",
    )


CFG_ALL_ON: dict = {}
CFG_TYPE_OFF: dict = {"compliance": {"type_aware_test_check": False}}
CFG_ROUTE_OFF: dict = {"compliance": {"route_registration_check": False}}


class TestTypeAwareTestChecker:

    def test_webui_tag_no_integration_test_gives_error(self, tmp_path: Path) -> None:
        spec = _spec(["webui"], ["TST-001"])
        tests_dir = tmp_path / ".sdd" / "tests"
        tests_dir.mkdir(parents=True)
        checker = TypeAwareTestChecker(tests_dir)
        issues = checker.check(spec, CFG_ALL_ON)
        assert len(issues) == 1
        assert issues[0].severity == "error"

    def test_api_tag_with_contract_test_no_issue(self, tmp_path: Path) -> None:
        spec = _spec(["api"], ["TST-001"])
        tests_dir = tmp_path / ".sdd" / "tests"
        contract_dir = tests_dir / "contract"
        contract_dir.mkdir(parents=True)
        (contract_dir / "TST-001-my-test.md").write_text(
            "---\nid: TST-001\nstufe: contract\n---\nbody\n"
        )
        checker = TypeAwareTestChecker(tests_dir)
        issues = checker.check(spec, CFG_ALL_ON)
        assert issues == []

    def test_no_type_tag_no_issue(self, tmp_path: Path) -> None:
        spec = _spec(["process", "validation"])
        tests_dir = tmp_path / ".sdd" / "tests"
        tests_dir.mkdir(parents=True)
        checker = TypeAwareTestChecker(tests_dir)
        issues = checker.check(spec, CFG_ALL_ON)
        assert issues == []

    def test_frontend_tag_with_integration_stufe_in_frontmatter_no_issue(self, tmp_path: Path) -> None:
        spec = _spec(["frontend"], ["TST-002"])
        tests_dir = tmp_path / ".sdd" / "tests"
        other_dir = tests_dir / "unit"
        other_dir.mkdir(parents=True)
        (other_dir / "TST-002-something.md").write_text(
            "---\nid: TST-002\nstufe: integration\n---\nbody\n"
        )
        checker = TypeAwareTestChecker(tests_dir)
        issues = checker.check(spec, CFG_ALL_ON)
        assert issues == []

    def test_disabled_check_no_issue(self, tmp_path: Path) -> None:
        spec = _spec(["webui"])
        tests_dir = tmp_path / ".sdd" / "tests"
        tests_dir.mkdir(parents=True)
        checker = TypeAwareTestChecker(tests_dir)
        issues = checker.check(spec, CFG_TYPE_OFF)
        assert issues == []


class TestRouteRegistrationChecker:

    def test_api_tag_without_include_router_gives_error(self, tmp_path: Path) -> None:
        spec = _spec(["api"])
        main_py = tmp_path / "tool" / "sdd_cli" / "web" / "api" / "main.py"
        main_py.parent.mkdir(parents=True)
        main_py.write_text("# no routers here\napp = FastAPI()\n")
        checker = RouteRegistrationChecker(tmp_path)
        issues = checker.check(spec, CFG_ALL_ON)
        assert len(issues) == 1
        assert issues[0].severity == "error"

    def test_api_tag_with_include_router_no_issue(self, tmp_path: Path) -> None:
        spec = _spec(["api"])
        main_py = tmp_path / "tool" / "sdd_cli" / "web" / "api" / "main.py"
        main_py.parent.mkdir(parents=True)
        main_py.write_text("app.include_router(my_router)\n")
        checker = RouteRegistrationChecker(tmp_path)
        issues = checker.check(spec, CFG_ALL_ON)
        assert issues == []

    def test_nonexistent_entry_point_no_issue(self, tmp_path: Path) -> None:
        spec = _spec(["api"])
        checker = RouteRegistrationChecker(tmp_path)
        issues = checker.check(spec, CFG_ALL_ON)
        assert issues == []

    def test_disabled_check_no_issue(self, tmp_path: Path) -> None:
        spec = _spec(["api"])
        main_py = tmp_path / "tool" / "sdd_cli" / "web" / "api" / "main.py"
        main_py.parent.mkdir(parents=True)
        main_py.write_text("# kein router\n")
        checker = RouteRegistrationChecker(tmp_path)
        issues = checker.check(spec, CFG_ROUTE_OFF)
        assert issues == []

    def test_non_api_spec_no_issue(self, tmp_path: Path) -> None:
        spec = _spec(["webui"])
        checker = RouteRegistrationChecker(tmp_path)
        issues = checker.check(spec, CFG_ALL_ON)
        assert issues == []
