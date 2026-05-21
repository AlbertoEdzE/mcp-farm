"""Cluster C1 — Local Environment tests.

Test classes:
  TestDockerComposeStructure  — structural tests (always run, no stack required)
  TestInfrastructureStack     — postgres + redis integration (require_infra_stack)
  TestContextForgeStack       — gateway + registry integration (require_full_stack)

Run structural tests only (no stack needed):
  make test CLUSTER=c1

Run infrastructure tests (start infra first):
  make local-up -- --infra-only && make test CLUSTER=c1

Run all C1 tests (full stack):
  make local-up && make test CLUSTER=c1
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest
import yaml

_REPO_ROOT = Path(__file__).parent.parent
_FIXTURES_DIR = _REPO_ROOT / "tests" / "fixtures"

REQUIRED_COMPOSE_SERVICES = {"contextforge", "postgres", "redis"}
REQUIRED_CONFIG_SECTIONS = {"gateway", "registry", "database", "cache", "proxy", "virtual_servers"}

# ---------------------------------------------------------------------------
# Structural tests — always run, no running services required
# ---------------------------------------------------------------------------


class TestDockerComposeStructure:
    def test_docker_compose_file_exists(self) -> None:
        """docker-compose.yml must exist at the repository root."""
        assert (_REPO_ROOT / "docker-compose.yml").is_file(), (
            "docker-compose.yml not found. Create it per MF-E02-T01."
        )

    def test_docker_compose_defines_required_services(self) -> None:
        """docker-compose.yml must define contextforge, postgres, and redis services."""
        content = (_REPO_ROOT / "docker-compose.yml").read_text()
        data = yaml.safe_load(content)
        defined = set(data.get("services", {}).keys())
        missing = REQUIRED_COMPOSE_SERVICES - defined
        assert not missing, (
            f"docker-compose.yml is missing services: {missing}"
        )

    def test_docker_compose_no_hardcoded_credentials(self) -> None:
        """docker-compose.yml must not contain hardcoded passwords or secrets.

        All sensitive values must be read from environment variables
        using the ${VAR_NAME} syntax or be clearly marked as placeholders.
        """
        content = (_REPO_ROOT / "docker-compose.yml").read_text()
        import re

        cred_assignment = re.compile(
            r"(?:PASSWORD|SECRET|KEY|TOKEN)\s*:\s*(.+)",
            re.IGNORECASE,
        )
        suspicious = []
        for match in cred_assignment.finditer(content):
            value = match.group(1).strip().strip('"').strip("'")
            is_env_ref = value.startswith("${") or value.startswith("$")
            is_placeholder = value.startswith("<")
            is_empty = not value
            if not (is_env_ref or is_placeholder or is_empty):
                suspicious.append(match.group(0).strip())
        assert not suspicious, (
            f"docker-compose.yml may contain hardcoded credentials: {suspicious}"
        )

    def test_docker_compose_health_checks_defined(self) -> None:
        """All three services must have health checks defined."""
        content = (_REPO_ROOT / "docker-compose.yml").read_text()
        data = yaml.safe_load(content)
        services_without_healthcheck = [
            svc for svc, cfg in data.get("services", {}).items()
            if "healthcheck" not in cfg
        ]
        assert not services_without_healthcheck, (
            f"Services missing health checks: {services_without_healthcheck}"
        )

    def test_docker_compose_named_volume_defined(self) -> None:
        """postgres_data named volume must be declared in the volumes section."""
        content = (_REPO_ROOT / "docker-compose.yml").read_text()
        data = yaml.safe_load(content)
        assert "postgres_data" in data.get("volumes", {}), (
            "Named volume 'postgres_data' not found in docker-compose.yml volumes section."
        )

    def test_contextforge_config_template_complete(self) -> None:
        """config/contextforge.example.yaml must have all required top-level sections."""
        config_path = _REPO_ROOT / "config" / "contextforge.example.yaml"
        assert config_path.is_file(), "config/contextforge.example.yaml not found."
        content = yaml.safe_load(config_path.read_text())
        # The template has commented sections — parse what's present
        raw_text = config_path.read_text()
        missing = [
            section for section in REQUIRED_CONFIG_SECTIONS
            if section not in raw_text
        ]
        assert not missing, (
            f"config/contextforge.example.yaml is missing sections: {missing}"
        )

    def test_expose_container_port_flag_documented(self) -> None:
        """config/contextforge.example.yaml must reference the container port exposure flag."""
        config_path = _REPO_ROOT / "config" / "contextforge.example.yaml"
        content = config_path.read_text()
        assert "expose_container_port" in content, (
            "expose_container_port flag not found in contextforge.example.yaml. "
            "This flag is required. See doc/ADR/ADR-001-gke-over-cloud-run.md."
        )

    def test_synthetic_fixtures_directory_exists(self) -> None:
        """tests/fixtures/ directory must exist."""
        assert _FIXTURES_DIR.is_dir(), (
            "tests/fixtures/ directory not found. "
            "Run: make generate-data"
        )

    def test_synthetic_fixtures_are_valid_json(self) -> None:
        """All .json files in tests/fixtures/ must be valid JSON."""
        fixture_files = list(_FIXTURES_DIR.glob("*.json"))
        if not fixture_files:
            pytest.skip(
                "No fixture files found. Run: make generate-data"
            )
        invalid = []
        for f in fixture_files:
            try:
                json.loads(f.read_text())
            except json.JSONDecodeError as exc:
                invalid.append(f"{f.name}: {exc}")
        assert not invalid, f"Invalid JSON fixtures: {invalid}"

    def test_virtual_server_fixture_schema(self) -> None:
        """tests/fixtures/virtual_server_definition.json must have the required structure."""
        fixture_path = _FIXTURES_DIR / "virtual_server_definition.json"
        if not fixture_path.is_file():
            pytest.skip("virtual_server_definition.json not found. Run: make generate-data")
        data = json.loads(fixture_path.read_text())
        assert "name" in data, "virtual_server_definition.json missing 'name' key."
        assert "tools" in data, "virtual_server_definition.json missing 'tools' key."
        assert isinstance(data["tools"], list), "'tools' must be a list."
        assert len(data["tools"]) >= 2, "At least 2 tools required in the virtual server."
        tool_names = {t["name"] for t in data["tools"]}
        assert "tool-alpha" in tool_names, "tool-alpha missing from virtual server definition."
        assert "tool-beta" in tool_names, "tool-beta missing from virtual server definition."

    def test_proxy_registration_fixture_schema(self) -> None:
        """tests/fixtures/mcp_proxy_registration.json must have the required structure."""
        fixture_path = _FIXTURES_DIR / "mcp_proxy_registration.json"
        if not fixture_path.is_file():
            pytest.skip("mcp_proxy_registration.json not found. Run: make generate-data")
        data = json.loads(fixture_path.read_text())
        for key in ("name", "url", "transport", "auth"):
            assert key in data, f"mcp_proxy_registration.json missing '{key}' key."

    def test_local_up_script_accepts_help(self) -> None:
        """scripts/local_up.sh --help must exit with code 0."""
        result = subprocess.run(
            [str(_REPO_ROOT / "scripts" / "local_up.sh"), "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"local_up.sh --help exited {result.returncode}.\n{result.stdout}\n{result.stderr}"
        )
        assert "--infra-only" in result.stdout, (
            "local_up.sh --help should document the --infra-only option."
        )

    def test_local_down_script_accepts_help(self) -> None:
        """scripts/local_down.sh --help must exit with code 0."""
        result = subprocess.run(
            [str(_REPO_ROOT / "scripts" / "local_down.sh"), "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"local_down.sh --help exited {result.returncode}.\n{result.stdout}\n{result.stderr}"
        )

    def test_generate_data_script_accepts_help(self) -> None:
        """scripts/generate_synthetic_data.py --help must exit with code 0."""
        result = subprocess.run(
            [str(_REPO_ROOT / ".venv" / "bin" / "python"),
             str(_REPO_ROOT / "scripts" / "generate_synthetic_data.py"), "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"generate_synthetic_data.py --help exited {result.returncode}.\n"
            f"{result.stdout}\n{result.stderr}"
        )


# ---------------------------------------------------------------------------
# Infrastructure integration tests — require postgres + redis running
# ---------------------------------------------------------------------------


class TestInfrastructureStack:
    @pytest.fixture(autouse=True)
    def _need_infra(self, require_infra_stack: None) -> None:
        pass

    def test_docker_compose_infra_services_healthy(self) -> None:
        """postgres and redis must show as healthy in docker compose ps."""
        result = subprocess.run(
            ["docker", "compose", "ps", "--format", "json"],
            cwd=str(_REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"docker compose ps failed: {result.stderr}"
        )
        # docker compose ps --format json produces one JSON object per line
        services: dict[str, str] = {}
        for line in result.stdout.strip().splitlines():
            try:
                obj = json.loads(line)
                name = obj.get("Service", obj.get("Name", ""))
                health = obj.get("Health", obj.get("Status", ""))
                if name:
                    services[name] = health
            except json.JSONDecodeError:
                continue

        for svc in ("postgres", "redis"):
            assert svc in services, (
                f"Service '{svc}' not found in docker compose ps output. "
                f"Found: {list(services.keys())}"
            )
            assert "healthy" in services[svc].lower(), (
                f"Service '{svc}' is not healthy. Status: '{services[svc]}'"
            )

    def test_postgres_accepts_connections(self) -> None:
        """PostgreSQL must accept a connection and execute SELECT 1."""
        import psycopg2  # type: ignore[import]

        user = os.environ.get("CLOUDSQL_USER")
        password = os.environ.get("CLOUDSQL_PASSWORD")
        dbname = os.environ.get("CLOUDSQL_DATABASE_NAME", "contextforge")
        port = int(os.environ.get("LOCAL_POSTGRES_PORT", "5432"))

        if not user or not password:
            pytest.skip("CLOUDSQL_USER or CLOUDSQL_PASSWORD not set in .env.")

        conn = psycopg2.connect(
            host="localhost",
            port=port,
            user=user,
            password=password,
            dbname=dbname,
            connect_timeout=5,
        )
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                result = cur.fetchone()
                assert result == (1,), f"SELECT 1 returned unexpected result: {result}"
        finally:
            conn.close()

    def test_redis_responds_to_ping(self) -> None:
        """Redis must respond PONG to a PING command."""
        import redis as redis_module

        port = int(os.environ.get("LOCAL_REDIS_PORT", "6379"))
        client = redis_module.Redis(host="localhost", port=port, socket_timeout=5)
        response = client.ping()
        assert response is True, f"Redis PING returned unexpected response: {response}"


# ---------------------------------------------------------------------------
# Full stack integration tests — require ContextForge gateway running
# ---------------------------------------------------------------------------


class TestContextForgeStack:
    @pytest.fixture(autouse=True)
    def _need_full_stack(self, require_full_stack: None) -> None:
        pass

    def test_gateway_port_reachable(self, gateway_base_url: str) -> None:
        """ContextForge AI Gateway TCP port must be reachable."""
        import socket
        from urllib.parse import urlparse
        parsed = urlparse(gateway_base_url)
        port = parsed.port or 8080
        try:
            sock = socket.create_connection(("localhost", port), timeout=3.0)
            sock.close()
        except (socket.timeout, ConnectionRefusedError, OSError) as exc:
            pytest.fail(f"Gateway port {port} not reachable: {exc}")

    def test_registry_port_reachable(self, registry_base_url: str) -> None:
        """ContextForge Config Registry TCP port must be reachable."""
        import socket
        from urllib.parse import urlparse
        parsed = urlparse(registry_base_url)
        port = parsed.port or 8081
        try:
            sock = socket.create_connection(("localhost", port), timeout=3.0)
            sock.close()
        except (socket.timeout, ConnectionRefusedError, OSError) as exc:
            pytest.fail(f"Registry port {port} not reachable: {exc}")

    def test_docker_compose_all_services_healthy(self) -> None:
        """All three services (contextforge, postgres, redis) must be healthy."""
        result = subprocess.run(
            ["docker", "compose", "ps", "--format", "json"],
            cwd=str(_REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"docker compose ps failed: {result.stderr}"

        services: dict[str, str] = {}
        for line in result.stdout.strip().splitlines():
            try:
                obj = json.loads(line)
                name = obj.get("Service", obj.get("Name", ""))
                health = obj.get("Health", obj.get("Status", ""))
                if name:
                    services[name] = health
            except json.JSONDecodeError:
                continue

        for svc in REQUIRED_COMPOSE_SERVICES:
            assert svc in services, (
                f"Service '{svc}' not found in docker compose ps. "
                f"Found: {list(services.keys())}"
            )
            assert "healthy" in services[svc].lower(), (
                f"Service '{svc}' not healthy. Status: '{services[svc]}'"
            )
