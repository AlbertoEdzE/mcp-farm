"""Cluster C6 — Documentation and Runbook tests.

All tests in this file are structural (always run, no running services required).
They verify the completeness and consistency of project documentation.

Run:
  make test CLUSTER=c6

Progressive run (full suite):
  make test CLUSTER=c0,c1,c2,c3,c4,c5,c6
"""
from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent


class TestDocumentation:

    # ------------------------------------------------------------------
    # README
    # ------------------------------------------------------------------

    def test_readme_exists(self) -> None:
        """README.md must exist at the repository root."""
        assert (_REPO_ROOT / "README.md").is_file(), "README.md not found."

    def test_readme_has_prerequisites_section(self) -> None:
        """README.md must have a Prerequisites section."""
        content = (_REPO_ROOT / "README.md").read_text()
        assert "Prerequisites" in content, (
            "README.md must include a 'Prerequisites' section."
        )

    def test_readme_has_quick_start_section(self) -> None:
        """README.md must have a Quick Start section."""
        content = (_REPO_ROOT / "README.md").read_text()
        assert "Quick Start" in content, (
            "README.md must include a 'Quick Start' section."
        )

    def test_readme_has_make_targets_section(self) -> None:
        """README.md must document the available Make targets."""
        content = (_REPO_ROOT / "README.md").read_text()
        assert "make" in content.lower(), (
            "README.md must document the Make targets."
        )

    def test_readme_has_testing_section(self) -> None:
        """README.md must explain how to run the test suite."""
        content = (_REPO_ROOT / "README.md").read_text()
        assert "test" in content.lower(), (
            "README.md must document how to run tests."
        )

    def test_readme_has_cluster_map(self) -> None:
        """README.md must include a cluster map (C0 through C6)."""
        content = (_REPO_ROOT / "README.md").read_text()
        for cluster in ("C0", "C1", "C2", "C3", "C4", "C5", "C6"):
            assert cluster in content, (
                f"README.md cluster map must include '{cluster}'."
            )

    def test_readme_references_all_adrs(self) -> None:
        """README.md must reference all four ADRs."""
        content = (_REPO_ROOT / "README.md").read_text()
        for adr in ("ADR-001", "ADR-002", "ADR-003", "ADR-004"):
            assert adr in content, (
                f"README.md must reference {adr}."
            )

    def test_readme_references_open_questions(self) -> None:
        """README.md must document at least the Q1 open question."""
        content = (_REPO_ROOT / "README.md").read_text()
        assert "Q1" in content, (
            "README.md must reference Q1 (IBM ContextForge image URI) as an open question."
        )

    # ------------------------------------------------------------------
    # Runbook
    # ------------------------------------------------------------------

    def test_runbook_exists(self) -> None:
        """doc/Runbook.md must exist."""
        assert (_REPO_ROOT / "doc" / "Runbook.md").is_file(), (
            "doc/Runbook.md not found. "
            "See doc/Specify.md Section 16 acceptance criterion 8."
        )

    def test_runbook_has_prerequisites_section(self) -> None:
        """doc/Runbook.md must have a Prerequisites section."""
        content = (_REPO_ROOT / "doc" / "Runbook.md").read_text()
        assert "Prerequisites" in content, (
            "doc/Runbook.md must include a 'Prerequisites' section."
        )

    def test_runbook_references_make_local_up(self) -> None:
        """doc/Runbook.md must document the make local-up command."""
        content = (_REPO_ROOT / "doc" / "Runbook.md").read_text()
        assert "local-up" in content, (
            "doc/Runbook.md must document the 'make local-up' step."
        )

    def test_runbook_references_make_gke_provision(self) -> None:
        """doc/Runbook.md must document the make gke-provision command."""
        content = (_REPO_ROOT / "doc" / "Runbook.md").read_text()
        assert "gke-provision" in content, (
            "doc/Runbook.md must document the 'make gke-provision' step."
        )

    def test_runbook_references_make_gke_deploy(self) -> None:
        """doc/Runbook.md must document the make gke-deploy command."""
        content = (_REPO_ROOT / "doc" / "Runbook.md").read_text()
        assert "gke-deploy" in content, (
            "doc/Runbook.md must document the 'make gke-deploy' step."
        )

    def test_runbook_references_make_gke_teardown(self) -> None:
        """doc/Runbook.md must document the make gke-teardown command."""
        content = (_REPO_ROOT / "doc" / "Runbook.md").read_text()
        assert "gke-teardown" in content, (
            "doc/Runbook.md must document the 'make gke-teardown' step."
        )

    def test_runbook_references_register_proxy(self) -> None:
        """doc/Runbook.md must document the make register-proxy command."""
        content = (_REPO_ROOT / "doc" / "Runbook.md").read_text()
        assert "register-proxy" in content, (
            "doc/Runbook.md must document the 'make register-proxy' step."
        )

    def test_runbook_references_create_virtual_server(self) -> None:
        """doc/Runbook.md must document the make create-virtual-server command."""
        content = (_REPO_ROOT / "doc" / "Runbook.md").read_text()
        assert "create-virtual-server" in content, (
            "doc/Runbook.md must document the 'make create-virtual-server' step."
        )

    def test_runbook_has_troubleshooting_section(self) -> None:
        """doc/Runbook.md must include a Troubleshooting section."""
        content = (_REPO_ROOT / "doc" / "Runbook.md").read_text()
        assert "Troubleshooting" in content, (
            "doc/Runbook.md must include a 'Troubleshooting' section."
        )

    def test_runbook_documents_port_exposure_issue(self) -> None:
        """doc/Runbook.md Troubleshooting section must cover the CF_EXPOSE_CONTAINER_PORT issue."""
        content = (_REPO_ROOT / "doc" / "Runbook.md").read_text()
        assert "CF_EXPOSE_CONTAINER_PORT" in content, (
            "doc/Runbook.md must document the CF_EXPOSE_CONTAINER_PORT troubleshooting step "
            "(root cause of the Cloud Run failure, per ADR-001)."
        )

    def test_runbook_has_acceptance_criteria_checklist(self) -> None:
        """doc/Runbook.md must include the project-level acceptance criteria checklist."""
        content = (_REPO_ROOT / "doc" / "Runbook.md").read_text()
        assert "Acceptance Criteria" in content, (
            "doc/Runbook.md must include the project-level acceptance criteria checklist "
            "from doc/Specify.md Section 16."
        )

    def test_runbook_references_open_questions(self) -> None:
        """doc/Runbook.md must document the open questions that block GKE deployment."""
        content = (_REPO_ROOT / "doc" / "Runbook.md").read_text()
        for q in ("Q1", "Q2", "Q4", "Q6"):
            assert q in content, (
                f"doc/Runbook.md must reference open question {q}."
            )

    # ------------------------------------------------------------------
    # ADR completeness
    # ------------------------------------------------------------------

    def test_all_four_adrs_exist(self) -> None:
        """All four Architecture Decision Records (ADR-001 through ADR-004) must exist."""
        for adr_file in (
            "ADR-001-gke-over-cloud-run.md",
            "ADR-002-managed-data-services.md",
            "ADR-003-mcp-proxy-oauth-strategy.md",
            "ADR-004-virtual-server-as-access-boundary.md",
        ):
            path = _REPO_ROOT / "doc" / "ADR" / adr_file
            assert path.is_file(), (
                f"doc/ADR/{adr_file} not found."
            )

    def test_specify_md_exists(self) -> None:
        """doc/Specify.md must exist."""
        assert (_REPO_ROOT / "doc" / "Specify.md").is_file(), (
            "doc/Specify.md not found."
        )

    def test_plan_md_exists(self) -> None:
        """doc/Plan.md must exist."""
        assert (_REPO_ROOT / "doc" / "Plan.md").is_file(), (
            "doc/Plan.md not found."
        )

    # ------------------------------------------------------------------
    # Test file completeness
    # ------------------------------------------------------------------

    def test_all_cluster_test_files_exist(self) -> None:
        """Test files for all seven clusters (C0 through C6) must exist."""
        for i in range(7):
            pattern = list((_REPO_ROOT / "tests").glob(f"test_c{i}_*.py"))
            assert len(pattern) == 1, (
                f"Expected exactly one test file matching tests/test_c{i}_*.py. "
                f"Found: {[p.name for p in pattern]}"
            )

    def test_conftest_exists(self) -> None:
        """tests/conftest.py must exist."""
        assert (_REPO_ROOT / "tests" / "conftest.py").is_file(), (
            "tests/conftest.py not found."
        )

    def test_conftest_has_require_full_stack_fixture(self) -> None:
        """tests/conftest.py must define the require_full_stack fixture."""
        content = (_REPO_ROOT / "tests" / "conftest.py").read_text()
        assert "require_full_stack" in content, (
            "tests/conftest.py must define the 'require_full_stack' session fixture."
        )

    def test_conftest_has_require_infra_stack_fixture(self) -> None:
        """tests/conftest.py must define the require_infra_stack fixture."""
        content = (_REPO_ROOT / "tests" / "conftest.py").read_text()
        assert "require_infra_stack" in content, (
            "tests/conftest.py must define the 'require_infra_stack' session fixture."
        )
