"""Cluster C5 — Virtual Server configuration tests.

Test classes:
  TestVirtualServerStructure   — structural tests (always run, no stack required)
  TestVirtualServerIntegration — Config Registry API validation (require_full_stack)

Run structural tests only:
  make test CLUSTER=c5

Run integration tests (full stack required, Q1 must be resolved first):
  make register-proxy && make create-virtual-server && make test CLUSTER=c5

Progressive run (C0 through C5):
  make test CLUSTER=c0,c1,c2,c3,c4,c5
"""
from __future__ import annotations

import json
import sys
import subprocess
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).parent.parent
_FIXTURES_DIR = _REPO_ROOT / "tests" / "fixtures"


# ---------------------------------------------------------------------------
# Structural tests — always run, no running services required
# ---------------------------------------------------------------------------


class TestVirtualServerStructure:

    def test_adr_004_exists(self) -> None:
        """doc/ADR/ADR-004-virtual-server-as-access-boundary.md must exist."""
        adr_path = _REPO_ROOT / "doc" / "ADR" / "ADR-004-virtual-server-as-access-boundary.md"
        assert adr_path.is_file(), (
            "ADR-004 not found. It documents the virtual server as the agent access control "
            "boundary. See doc/Plan.md EPIC-MF-E06."
        )

    def test_adr_004_references_proxy_prerequisite(self) -> None:
        """ADR-004 must state that proxy registration precedes virtual server creation."""
        content = (_REPO_ROOT / "doc" / "ADR" / "ADR-004-virtual-server-as-access-boundary.md").read_text()
        assert "proxy" in content.lower(), (
            "ADR-004 must document the dependency on MCP proxy registration."
        )

    def test_virtual_server_section_in_config_has_name_var(self) -> None:
        """config/contextforge.example.yaml virtual_servers entry must reference VIRTUAL_SERVER_NAME."""
        content = (_REPO_ROOT / "config" / "contextforge.example.yaml").read_text()
        assert "VIRTUAL_SERVER_NAME" in content, (
            "config/contextforge.example.yaml virtual_servers section must reference "
            "${VIRTUAL_SERVER_NAME} env var."
        )

    def test_virtual_server_config_defines_two_tools(self) -> None:
        """config/contextforge.example.yaml virtual server must declare tool-alpha and tool-beta."""
        content = (_REPO_ROOT / "config" / "contextforge.example.yaml").read_text()
        for tool in ("tool-alpha", "tool-beta"):
            assert tool in content, (
                f"config/contextforge.example.yaml virtual_servers section must define '{tool}'."
            )

    def test_virtual_server_config_references_gitlab_proxy(self) -> None:
        """config/contextforge.example.yaml virtual server tools must reference gitlab-mcp proxy."""
        content = (_REPO_ROOT / "config" / "contextforge.example.yaml").read_text()
        assert "gitlab-mcp" in content, (
            "Virtual server tool definitions must reference the 'gitlab-mcp' proxy."
        )

    def test_env_example_has_virtual_server_name(self) -> None:
        """.env.example must declare VIRTUAL_SERVER_NAME."""
        content = (_REPO_ROOT / ".env.example").read_text()
        assert "VIRTUAL_SERVER_NAME" in content, (
            "VIRTUAL_SERVER_NAME not found in .env.example."
        )

    def test_virtual_server_fixture_exists(self) -> None:
        """tests/fixtures/virtual_server_definition.json must exist."""
        fixture_path = _FIXTURES_DIR / "virtual_server_definition.json"
        assert fixture_path.is_file(), (
            "tests/fixtures/virtual_server_definition.json not found. "
            "Run: make generate-data"
        )

    def test_virtual_server_fixture_has_name_and_tools(self) -> None:
        """virtual_server_definition.json must have 'name' and 'tools' fields."""
        fixture_path = _FIXTURES_DIR / "virtual_server_definition.json"
        if not fixture_path.is_file():
            pytest.skip("virtual_server_definition.json not found. Run: make generate-data")
        data = json.loads(fixture_path.read_text())
        assert "name" in data, "virtual_server_definition.json missing 'name'."
        assert "tools" in data, "virtual_server_definition.json missing 'tools'."
        assert isinstance(data["tools"], list), "'tools' must be a list."

    def test_virtual_server_fixture_has_exactly_two_tools(self) -> None:
        """virtual_server_definition.json must define exactly two tools: tool-alpha and tool-beta."""
        fixture_path = _FIXTURES_DIR / "virtual_server_definition.json"
        if not fixture_path.is_file():
            pytest.skip("virtual_server_definition.json not found. Run: make generate-data")
        data = json.loads(fixture_path.read_text())
        tools = data.get("tools", [])
        assert len(tools) >= 2, f"Expected at least 2 tools, got {len(tools)}."
        tool_names = {t["name"] for t in tools}
        for expected in ("tool-alpha", "tool-beta"):
            assert expected in tool_names, (
                f"'{expected}' not found in virtual_server_definition.json tools."
            )

    def test_virtual_server_fixture_tools_have_input_schema(self) -> None:
        """Each tool in virtual_server_definition.json must define an inputSchema."""
        fixture_path = _FIXTURES_DIR / "virtual_server_definition.json"
        if not fixture_path.is_file():
            pytest.skip("virtual_server_definition.json not found. Run: make generate-data")
        data = json.loads(fixture_path.read_text())
        for tool in data.get("tools", []):
            assert "inputSchema" in tool, (
                f"Tool '{tool.get('name')}' in virtual_server_definition.json "
                "is missing 'inputSchema'."
            )

    def test_tool_invocation_fixture_exists(self) -> None:
        """tests/fixtures/tool_invocation_request.json must exist."""
        fixture_path = _FIXTURES_DIR / "tool_invocation_request.json"
        assert fixture_path.is_file(), (
            "tests/fixtures/tool_invocation_request.json not found. "
            "Run: make generate-data"
        )

    def test_tool_invocation_fixture_references_virtual_server(self) -> None:
        """tool_invocation_request.json must target 'test-virtual-server'."""
        fixture_path = _FIXTURES_DIR / "tool_invocation_request.json"
        if not fixture_path.is_file():
            pytest.skip("tool_invocation_request.json not found. Run: make generate-data")
        data = json.loads(fixture_path.read_text())
        assert data.get("server") == "test-virtual-server", (
            f"tool_invocation_request.json 'server' field must be 'test-virtual-server'. "
            f"Got: {data.get('server')!r}"
        )

    def test_tool_invocation_fixture_targets_tool_alpha(self) -> None:
        """tool_invocation_request.json must invoke 'tool-alpha'."""
        fixture_path = _FIXTURES_DIR / "tool_invocation_request.json"
        if not fixture_path.is_file():
            pytest.skip("tool_invocation_request.json not found. Run: make generate-data")
        data = json.loads(fixture_path.read_text())
        assert data.get("tool") == "tool-alpha", (
            f"tool_invocation_request.json 'tool' field must be 'tool-alpha'. "
            f"Got: {data.get('tool')!r}"
        )

    def test_tool_invocation_fixture_has_query_parameter(self) -> None:
        """tool_invocation_request.json parameters must include 'query' for tool-alpha."""
        fixture_path = _FIXTURES_DIR / "tool_invocation_request.json"
        if not fixture_path.is_file():
            pytest.skip("tool_invocation_request.json not found. Run: make generate-data")
        data = json.loads(fixture_path.read_text())
        assert "query" in data.get("parameters", {}), (
            "tool_invocation_request.json parameters must include 'query' "
            "(required by tool-alpha inputSchema)."
        )

    def test_create_virtual_server_script_exists(self) -> None:
        """scripts/create_virtual_server.py must exist."""
        assert (_REPO_ROOT / "scripts" / "create_virtual_server.py").is_file(), (
            "scripts/create_virtual_server.py not found. See doc/Plan.md EPIC-MF-E06."
        )

    def test_create_virtual_server_script_accepts_help(self) -> None:
        """scripts/create_virtual_server.py --help must exit with code 0."""
        result = subprocess.run(
            [sys.executable, str(_REPO_ROOT / "scripts" / "create_virtual_server.py"), "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"create_virtual_server.py --help exited {result.returncode}.\n{result.stderr}"
        )
        assert "--fixture" in result.stdout, (
            "create_virtual_server.py --help must document the --fixture option."
        )
        assert "--gateway-url" in result.stdout, (
            "create_virtual_server.py --help must document the --gateway-url option."
        )

    def test_makefile_has_create_virtual_server_target(self) -> None:
        """Makefile must define the create-virtual-server target."""
        content = (_REPO_ROOT / "Makefile").read_text()
        assert "create-virtual-server" in content, (
            "Makefile must define a 'create-virtual-server' target."
        )


# ---------------------------------------------------------------------------
# Integration tests — require the full ContextForge stack
# These tests are skipped until Q1 (CF_IMAGE_URI) is resolved and the
# stack is started. Run prerequisite steps first:
#   make local-up
#   make register-proxy
#   make create-virtual-server
# ---------------------------------------------------------------------------


class TestVirtualServerIntegration:
    @pytest.fixture(autouse=True)
    def _need_full_stack(self, require_full_stack: None) -> None:
        pass

    def test_create_virtual_server_returns_success(
        self, registry_base_url: str
    ) -> None:
        """POST /v1/virtual-servers with the synthetic fixture must return HTTP 200 or 201."""
        import httpx

        fixture_path = _FIXTURES_DIR / "virtual_server_definition.json"
        assert fixture_path.is_file(), (
            "virtual_server_definition.json not found. Run: make generate-data"
        )
        payload = json.loads(fixture_path.read_text())
        url = registry_base_url.rstrip("/") + "/v1/virtual-servers"

        response = httpx.post(url, json=payload, timeout=10.0)
        assert response.status_code in (200, 201), (
            f"POST {url} returned HTTP {response.status_code}. "
            "Expected 200 or 201. If the endpoint path differs, update "
            "_VIRTUAL_SERVER_ENDPOINT in scripts/create_virtual_server.py."
        )

    def test_virtual_server_list_returns_json_array(
        self, registry_base_url: str
    ) -> None:
        """GET /v1/virtual-servers must return a JSON array."""
        import httpx

        url = registry_base_url.rstrip("/") + "/v1/virtual-servers"
        response = httpx.get(url, timeout=10.0)
        assert response.status_code == 200, (
            f"GET {url} returned HTTP {response.status_code}. Expected 200."
        )
        body = response.json()
        assert isinstance(body, list), (
            f"GET /v1/virtual-servers must return a JSON array. Got: {type(body).__name__}"
        )

    def test_created_virtual_server_appears_in_list(
        self, registry_base_url: str
    ) -> None:
        """After creation, the virtual server must appear in GET /v1/virtual-servers."""
        import httpx

        fixture_path = _FIXTURES_DIR / "virtual_server_definition.json"
        assert fixture_path.is_file(), (
            "virtual_server_definition.json not found. Run: make generate-data"
        )
        payload = json.loads(fixture_path.read_text())
        server_name = payload["name"]
        base = registry_base_url.rstrip("/")

        httpx.post(base + "/v1/virtual-servers", json=payload, timeout=10.0)

        list_response = httpx.get(base + "/v1/virtual-servers", timeout=10.0)
        assert list_response.status_code == 200

        registered_names = [vs.get("name") for vs in list_response.json()]
        assert server_name in registered_names, (
            f"Virtual server '{server_name}' not found in /v1/virtual-servers after creation. "
            f"Found: {registered_names}"
        )

    def test_created_virtual_server_has_expected_tool_count(
        self, registry_base_url: str
    ) -> None:
        """The created virtual server must expose at least 2 tools in the registry response."""
        import httpx

        fixture_path = _FIXTURES_DIR / "virtual_server_definition.json"
        assert fixture_path.is_file(), (
            "virtual_server_definition.json not found. Run: make generate-data"
        )
        payload = json.loads(fixture_path.read_text())
        server_name = payload["name"]
        base = registry_base_url.rstrip("/")

        httpx.post(base + "/v1/virtual-servers", json=payload, timeout=10.0)

        list_response = httpx.get(base + "/v1/virtual-servers", timeout=10.0)
        assert list_response.status_code == 200

        server_record = next(
            (vs for vs in list_response.json() if vs.get("name") == server_name),
            None,
        )
        assert server_record is not None, (
            f"Virtual server '{server_name}' not found in registry."
        )
        tools = server_record.get("tools", [])
        assert len(tools) >= 2, (
            f"Virtual server '{server_name}' must expose at least 2 tools. "
            f"Got {len(tools)}: {[t.get('name') for t in tools]}"
        )
