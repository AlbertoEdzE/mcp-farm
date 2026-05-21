"""Cluster C0 — Repository Foundation structural validation tests.

These tests verify the integrity of the repository structure itself:
directories exist, required files are present, the .env.example is complete,
Python packages are importable, Makefile targets are defined, no suspicious
credential patterns appear in committed files, and the install script is
executable. No running services are required.
"""
from __future__ import annotations

import importlib.util
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).parent.parent

# ---------------------------------------------------------------------------
# Canonical lists — derived from doc/Specify.md Section 13 and doc/Plan.md
# ---------------------------------------------------------------------------

REQUIRED_DIRECTORIES: list[str] = [
    "config",
    "doc",
    "doc/ADR",
    "gemesis",
    "k8s",
    "scripts",
    "tests",
    "tests/fixtures",
]

REQUIRED_FILES_C0: list[str] = [
    "config/contextforge.example.yaml",
    "config/gke.example.yaml",
    "doc/Specify.md",
    "doc/Plan.md",
    "k8s/namespace.yaml",
    "k8s/deployment.yaml",
    "k8s/service.yaml",
    "k8s/ingress.yaml",
    "k8s/configmap.yaml",
    "k8s/secrets.example.yaml",
    "scripts/install.sh",
    "scripts/local_up.sh",
    "scripts/local_down.sh",
    "scripts/gke_provision.sh",
    "scripts/gke_deploy.sh",
    "scripts/gke_teardown.sh",
    "scripts/run_tests.sh",
    "scripts/generate_synthetic_data.py",
    "tests/conftest.py",
    "tests/test_c0_foundation.py",
    ".env.example",
    "Makefile",
    "requirements.txt",
    "requirements-dev.txt",
    "README.md",
]

REQUIRED_ENV_VARIABLES: list[str] = [
    "GCP_PROJECT_ID",
    "GCP_REGION",
    "GCP_ZONE",
    "GKE_CLUSTER_NAME",
    "GKE_NAMESPACE",
    "GKE_NODE_MACHINE_TYPE",
    "GKE_NODE_COUNT",
    "CF_IMAGE_URI",
    "CF_IMAGE_TAG",
    "CF_GATEWAY_PORT",
    "CF_REGISTRY_PORT",
    "CF_EXPOSE_CONTAINER_PORT",
    "CF_GATEWAY_HEALTH_PATH",
    "CF_REGISTRY_HEALTH_PATH",
    "CLOUDSQL_INSTANCE_NAME",
    "CLOUDSQL_DATABASE_NAME",
    "CLOUDSQL_USER",
    "CLOUDSQL_PASSWORD",
    "CLOUDSQL_CONNECTION_STRING",
    "MEMORYSTORE_INSTANCE_NAME",
    "REDIS_HOST",
    "REDIS_PORT",
    "LOCAL_POSTGRES_PORT",
    "LOCAL_REDIS_PORT",
    "LOCAL_CF_GATEWAY_PORT",
    "LOCAL_CF_REGISTRY_PORT",
    "IBM_ENTITLEMENT_KEY",
    "GITLAB_MCP_URL",
    "GITLAB_OAUTH_CLIENT_ID",
    "GITLAB_OAUTH_CLIENT_SECRET",
    "VIRTUAL_SERVER_NAME",
    "TEST_SYNTHETIC_DATA_SEED",
    "TEST_TARGET",
    "TEST_GATEWAY_BASE_URL",
    "TEST_REGISTRY_BASE_URL",
]

REQUIRED_MAKEFILE_TARGETS: list[str] = [
    "help",
    "install",
    "local-up",
    "local-down",
    "gke-provision",
    "gke-deploy",
    "gke-teardown",
    "test",
    "lint",
    "typecheck",
    "generate-data",
    "register-proxy",
    "clean",
]

# Import name mapped from the pip package name
REQUIRED_PYTHON_PACKAGES: dict[str, str] = {
    "httpx": "httpx",
    "pydantic": "pydantic",
    "python-dotenv": "dotenv",
    "faker": "faker",
    "pyyaml": "yaml",
    "pytest": "pytest",
}

EXECUTABLE_SCRIPTS: list[str] = [
    "scripts/install.sh",
    "scripts/run_tests.sh",
    "scripts/local_up.sh",
    "scripts/local_down.sh",
    "scripts/gke_provision.sh",
    "scripts/gke_deploy.sh",
    "scripts/gke_teardown.sh",
]

# Patterns that indicate a real secret rather than a placeholder.
# Matches are failures. Placeholders of the form <...> or ${...} are allowed.
SUSPICIOUS_PATTERNS: list[tuple[str, str]] = [
    (r"AIza[0-9A-Za-z\-_]{35}", "Google API key"),
    (r"ya29\.[0-9A-Za-z\-_]{10,}", "Google OAuth access token"),
]

# File extensions that should never be committed
FORBIDDEN_EXTENSIONS: list[str] = [".key", ".pem"]

# File names that should never be committed
FORBIDDEN_FILENAMES: list[str] = [
    ".env",
    "kubeconfig",
    "credentials.json",
    "service-account.json",
    "k8s/secrets.yaml",
]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestDirectoryStructure:
    def test_required_directories_exist(self) -> None:
        """All directories specified in doc/Specify.md Section 13 must exist."""
        missing = [
            d for d in REQUIRED_DIRECTORIES
            if not (_REPO_ROOT / d).is_dir()
        ]
        assert not missing, (
            f"Missing directories: {missing}. "
            "Create them per doc/Plan.md MF-E01-T01."
        )

    def test_required_files_exist(self) -> None:
        """All files required after Cluster C0 must be present."""
        missing = [
            f for f in REQUIRED_FILES_C0
            if not (_REPO_ROOT / f).is_file()
        ]
        assert not missing, (
            f"Missing files: {missing}. "
            "Create them per doc/Plan.md EPIC-MF-E01."
        )


class TestEnvExample:
    def test_env_example_exists(self) -> None:
        """.env.example must exist at the repository root."""
        assert (_REPO_ROOT / ".env.example").is_file(), (
            ".env.example not found at repository root."
        )

    def test_env_example_complete(self) -> None:
        """.env.example must declare every variable in REQUIRED_ENV_VARIABLES."""
        content = (_REPO_ROOT / ".env.example").read_text()
        missing = [
            var for var in REQUIRED_ENV_VARIABLES
            if var not in content
        ]
        assert not missing, (
            f".env.example is missing the following variables: {missing}. "
            "Add them per doc/Plan.md MF-E01-T02."
        )

    def test_env_not_committed(self) -> None:
        """.env must not exist as a committed or uncommitted tracked file."""
        env_path = _REPO_ROOT / ".env"
        if env_path.exists():
            gitignore = (_REPO_ROOT / ".gitignore").read_text()
            assert ".env" in gitignore, (
                ".env exists but is not in .gitignore. "
                "This is a security violation per doc/Specify.md Section 2."
            )


class TestRequirements:
    def test_requirements_files_exist(self) -> None:
        """Both requirements.txt and requirements-dev.txt must exist."""
        for f in ("requirements.txt", "requirements-dev.txt"):
            assert (_REPO_ROOT / f).is_file(), f"{f} not found."

    def test_python_packages_importable(self) -> None:
        """All runtime packages in requirements.txt must be importable."""
        not_found = [
            pip_name
            for pip_name, import_name in REQUIRED_PYTHON_PACKAGES.items()
            if importlib.util.find_spec(import_name) is None
        ]
        assert not not_found, (
            f"The following packages are not importable: {not_found}. "
            "Run: make install"
        )

    def test_requirements_dev_includes_runtime(self) -> None:
        """requirements-dev.txt must include -r requirements.txt."""
        content = (_REPO_ROOT / "requirements-dev.txt").read_text()
        assert "-r requirements.txt" in content, (
            "requirements-dev.txt does not include '-r requirements.txt'."
        )


class TestMakefile:
    def test_makefile_exists(self) -> None:
        """Makefile must exist at the repository root."""
        assert (_REPO_ROOT / "Makefile").is_file(), "Makefile not found."

    def test_makefile_targets_present(self) -> None:
        """All required targets must be defined in the Makefile."""
        content = (_REPO_ROOT / "Makefile").read_text()
        missing = [
            target for target in REQUIRED_MAKEFILE_TARGETS
            if not re.search(rf"^{re.escape(target)}:", content, re.MULTILINE)
        ]
        assert not missing, (
            f"Makefile is missing targets: {missing}. "
            "Add them per doc/Plan.md MF-E01-T04."
        )

    def test_makefile_help_target_has_descriptions(self) -> None:
        """All targets must have ## descriptions for the help target."""
        content = (_REPO_ROOT / "Makefile").read_text()
        for target in REQUIRED_MAKEFILE_TARGETS:
            pattern = rf"^{re.escape(target)}:.*?##"
            assert re.search(pattern, content, re.MULTILINE), (
                f"Makefile target '{target}' is missing a ## description. "
                "The help target requires ## annotations."
            )


class TestScripts:
    def test_shell_scripts_executable(self) -> None:
        """All shell scripts must have the executable bit set."""
        not_executable = [
            s for s in EXECUTABLE_SCRIPTS
            if not os.access(_REPO_ROOT / s, os.X_OK)
        ]
        assert not not_executable, (
            f"Scripts missing executable bit: {not_executable}. "
            "Run: chmod +x <script>"
        )

    def test_install_script_help_exits_zero(self) -> None:
        """scripts/install.sh --help must exit with code 0."""
        result = subprocess.run(
            [str(_REPO_ROOT / "scripts" / "install.sh"), "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"install.sh --help exited with {result.returncode}.\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )

    def test_placeholder_scripts_accept_help(self) -> None:
        """All placeholder scripts must accept --help and exit with code 0."""
        placeholder_scripts = [
            "scripts/local_up.sh",
            "scripts/local_down.sh",
            "scripts/gke_provision.sh",
            "scripts/gke_deploy.sh",
            "scripts/gke_teardown.sh",
        ]
        failures = []
        for script in placeholder_scripts:
            result = subprocess.run(
                [str(_REPO_ROOT / script), "--help"],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                failures.append(f"{script} (exit {result.returncode})")
        assert not failures, (
            f"The following scripts failed --help: {failures}"
        )


class TestSecurityBaseline:
    def _iter_source_files(self) -> list[Path]:
        """Return all non-binary, non-git files in the repository."""
        excluded_dirs = {".git", ".venv", "venv", "__pycache__", "reports"}
        files = []
        for path in _REPO_ROOT.rglob("*"):
            if path.is_file() and not any(
                part in excluded_dirs for part in path.parts
            ):
                files.append(path)
        return files

    def test_no_forbidden_file_extensions(self) -> None:
        """Files with extensions .key or .pem must not exist in the repository."""
        found = [
            str(f.relative_to(_REPO_ROOT))
            for f in self._iter_source_files()
            if f.suffix in FORBIDDEN_EXTENSIONS
        ]
        assert not found, (
            f"Forbidden file types found: {found}. "
            "Remove them — they may contain private keys."
        )

    def test_no_forbidden_filenames(self) -> None:
        """Specific filenames that must not be committed must not exist (except as .example)."""
        found = []
        for forbidden in FORBIDDEN_FILENAMES:
            path = _REPO_ROOT / forbidden
            if path.exists():
                found.append(forbidden)
        assert not found, (
            f"Forbidden files found: {found}. "
            "These files must not be committed per doc/Specify.md Section 2."
        )

    def test_no_google_api_key_pattern_in_files(self) -> None:
        """No file should contain a pattern matching a Google API key."""
        pattern_str, pattern_name = SUSPICIOUS_PATTERNS[0]
        pattern = re.compile(pattern_str)
        matches = []
        for f in self._iter_source_files():
            try:
                content = f.read_text(errors="ignore")
                if pattern.search(content):
                    matches.append(str(f.relative_to(_REPO_ROOT)))
            except (OSError, UnicodeDecodeError):
                continue
        assert not matches, (
            f"Files containing a {pattern_name} pattern: {matches}. "
            "Remove credentials from source files."
        )

    def test_env_example_sensitive_values_are_placeholders(self) -> None:
        """Variables with sensitive names in .env.example must carry <...> placeholders.

        Non-sensitive operational defaults (port numbers, target names, boolean flags,
        seed values) may have real default values. Only variables whose names indicate
        a credential (PASSWORD, SECRET, KEY, TOKEN, ENTITLEMENT) are required to use
        the <...> placeholder convention.
        """
        sensitive_name_pattern = re.compile(
            r"(PASSWORD|SECRET|KEY|TOKEN|ENTITLEMENT)", re.IGNORECASE
        )
        placeholder_pattern = re.compile(r"^<[^>]+>$")

        content = (_REPO_ROOT / ".env.example").read_text()
        not_placeholders = []
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            var_name, _, value = line.partition("=")
            value = value.strip()
            if sensitive_name_pattern.search(var_name) and value:
                if not placeholder_pattern.match(value):
                    not_placeholders.append(line)
        assert not not_placeholders, (
            f"Sensitive variables in .env.example must use <...> placeholders. "
            f"Found non-placeholder values: {not_placeholders}"
        )
