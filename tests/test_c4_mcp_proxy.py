"""Cluster C4 — MCP Proxy Registration tests.

Test classes:
  TestMCPProxyStructure   — structural tests (always run, no stack required)
  TestMCPProxyIntegration — proxy API validation (require_full_stack)

Run structural tests only:
  make test CLUSTER=c4

Run integration tests (full stack required, Q1 and Q4 must be resolved):
  make local-up && make test CLUSTER=c4

Progressive run (C0 through C4):
  make test CLUSTER=c0,c1,c2,c3,c4
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).parent.parent
_FIXTURES_DIR = _REPO_ROOT / "tests" / "fixtures"


# ---------------------------------------------------------------------------
# Structural tests — always run, no running services required
# ---------------------------------------------------------------------------


class TestMCPProxyStructure:

    def test_adr_003_exists(self) -> None:
        """doc/ADR/ADR-003-mcp-proxy-oauth-strategy.md must exist."""
        adr_path = _REPO_ROOT / "doc" / "ADR" / "ADR-003-mcp-proxy-oauth-strategy.md"
        assert adr_path.is_file(), (
            "ADR-003 not found. It documents the OAuth 2.0 strategy for the GitLab MCP proxy. "
            "See doc/Plan.md EPIC-MF-E05."
        )

    def test_adr_003_references_q4(self) -> None:
        """ADR-003 must reference Q4 as the open question for OAuth registration type."""
        content = (_REPO_ROOT / "doc" / "ADR" / "ADR-003-mcp-proxy-oauth-strategy.md").read_text()
        assert "Q4" in content, (
            "ADR-003 must reference Q4 (GitLab OAuth registration type) as an unresolved item."
        )

    def test_proxy_section_in_config_template_has_gitlab_entry(self) -> None:
        """config/contextforge.example.yaml proxy section must include a gitlab-mcp entry."""
        content = (_REPO_ROOT / "config" / "contextforge.example.yaml").read_text()
        assert "gitlab-mcp" in content, (
            "config/contextforge.example.yaml must define a 'gitlab-mcp' proxy entry."
        )

    def test_proxy_config_references_oauth_env_vars(self) -> None:
        """config/contextforge.example.yaml proxy auth must reference the OAuth env vars."""
        content = (_REPO_ROOT / "config" / "contextforge.example.yaml").read_text()
        for var in ("GITLAB_OAUTH_CLIENT_ID", "GITLAB_OAUTH_CLIENT_SECRET", "GITLAB_MCP_URL"):
            assert var in content, (
                f"config/contextforge.example.yaml proxy section must reference ${{{var}}}."
            )

    def test_proxy_config_specifies_sse_transport(self) -> None:
        """config/contextforge.example.yaml GitLab proxy must specify transport: sse."""
        content = (_REPO_ROOT / "config" / "contextforge.example.yaml").read_text()
        assert "transport: sse" in content, (
            "GitLab proxy in config/contextforge.example.yaml must use transport: sse."
        )

    def test_env_example_has_gitlab_oauth_variables(self) -> None:
        """.env.example must declare all three GitLab OAuth variables."""
        content = (_REPO_ROOT / ".env.example").read_text()
        for var in ("GITLAB_MCP_URL", "GITLAB_OAUTH_CLIENT_ID", "GITLAB_OAUTH_CLIENT_SECRET"):
            assert var in content, (
                f"{var} not found in .env.example."
            )

    def test_proxy_fixture_exists(self) -> None:
        """tests/fixtures/mcp_proxy_registration.json must exist."""
        fixture_path = _FIXTURES_DIR / "mcp_proxy_registration.json"
        assert fixture_path.is_file(), (
            "tests/fixtures/mcp_proxy_registration.json not found. "
            "Run: make generate-data"
        )

    def test_proxy_fixture_has_required_fields(self) -> None:
        """mcp_proxy_registration.json must have name, url, transport, and auth fields."""
        fixture_path = _FIXTURES_DIR / "mcp_proxy_registration.json"
        if not fixture_path.is_file():
            pytest.skip("mcp_proxy_registration.json not found. Run: make generate-data")
        data = json.loads(fixture_path.read_text())
        for field in ("name", "url", "transport", "auth"):
            assert field in data, (
                f"mcp_proxy_registration.json is missing required field '{field}'."
            )

    def test_proxy_fixture_auth_type_is_oauth2(self) -> None:
        """mcp_proxy_registration.json auth.type must be 'oauth2'."""
        fixture_path = _FIXTURES_DIR / "mcp_proxy_registration.json"
        if not fixture_path.is_file():
            pytest.skip("mcp_proxy_registration.json not found. Run: make generate-data")
        data = json.loads(fixture_path.read_text())
        auth = data.get("auth", {})
        assert auth.get("type") == "oauth2", (
            f"mcp_proxy_registration.json auth.type must be 'oauth2'. Got: {auth.get('type')!r}"
        )

    def test_proxy_fixture_has_oauth_scopes(self) -> None:
        """mcp_proxy_registration.json auth must include OAuth scopes."""
        fixture_path = _FIXTURES_DIR / "mcp_proxy_registration.json"
        if not fixture_path.is_file():
            pytest.skip("mcp_proxy_registration.json not found. Run: make generate-data")
        data = json.loads(fixture_path.read_text())
        scopes = data.get("auth", {}).get("scopes", [])
        assert isinstance(scopes, list) and len(scopes) > 0, (
            "mcp_proxy_registration.json auth.scopes must be a non-empty list."
        )

    def test_register_proxy_script_exists(self) -> None:
        """scripts/register_proxy.py must exist."""
        assert (_REPO_ROOT / "scripts" / "register_proxy.py").is_file(), (
            "scripts/register_proxy.py not found. See doc/Plan.md EPIC-MF-E05."
        )

    def test_register_proxy_script_accepts_help(self) -> None:
        """scripts/register_proxy.py --help must exit with code 0."""
        result = subprocess.run(
            [
                sys.executable,
                str(_REPO_ROOT / "scripts" / "register_proxy.py"),
                "--help",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"register_proxy.py --help exited {result.returncode}.\n{result.stderr}"
        )
        assert "--fixture" in result.stdout, (
            "register_proxy.py --help must document the --fixture option."
        )
        assert "--registry-url" in result.stdout, (
            "register_proxy.py --help must document the --registry-url option."
        )

    def test_makefile_has_register_proxy_target(self) -> None:
        """Makefile must define the register-proxy target."""
        content = (_REPO_ROOT / "Makefile").read_text()
        assert "register-proxy" in content, (
            "Makefile must define a 'register-proxy' target."
        )

    def test_q4_documented_in_specify(self) -> None:
        """doc/Specify.md must have a Q4 row in the open questions table."""
        content = (_REPO_ROOT / "doc" / "Specify.md").read_text()
        q4_line = next(
            (line for line in content.splitlines() if line.strip().startswith("| Q4 |")),
            None,
        )
        assert q4_line is not None, (
            "Q4 row not found in doc/Specify.md Section 15. "
            "Q4 tracks GitLab OAuth registration type (Bala)."
        )


# ---------------------------------------------------------------------------
# Integration tests — require the full ContextForge stack
# These tests are skipped until Q1 (CF_IMAGE_URI) and Q4 (GitLab OAuth)
# are resolved and the stack is started with: make local-up
# ---------------------------------------------------------------------------


class TestMCPProxyIntegration:
    @pytest.fixture(autouse=True)
    def _need_full_stack(self, require_full_stack: None) -> None:
        pass

    def test_proxy_registration_returns_success(
        self, registry_base_url: str
    ) -> None:
        """POST /v1/proxies with the synthetic fixture must return HTTP 200 or 201."""
        import httpx

        fixture_path = _FIXTURES_DIR / "mcp_proxy_registration.json"
        assert fixture_path.is_file(), (
            "tests/fixtures/mcp_proxy_registration.json not found. Run: make generate-data"
        )
        payload = json.loads(fixture_path.read_text())
        url = registry_base_url.rstrip("/") + "/v1/proxies"

        response = httpx.post(url, json=payload, timeout=10.0)
        assert response.status_code in (200, 201), (
            f"POST {url} returned HTTP {response.status_code}. "
            "Expected 200 or 201. If the endpoint path differs, update _PROXY_ENDPOINT "
            "in scripts/register_proxy.py and recheck IBM ContextForge docs."
        )

    def test_proxy_list_returns_json_array(
        self, registry_base_url: str
    ) -> None:
        """GET /v1/proxies must return a JSON array."""
        import httpx

        url = registry_base_url.rstrip("/") + "/v1/proxies"
        response = httpx.get(url, timeout=10.0)
        assert response.status_code == 200, (
            f"GET {url} returned HTTP {response.status_code}. Expected 200."
        )
        body = response.json()
        assert isinstance(body, list), (
            f"GET /v1/proxies must return a JSON array. Got: {type(body).__name__}"
        )

    def test_registered_proxy_appears_in_list(
        self, registry_base_url: str
    ) -> None:
        """After registration, the proxy must appear in GET /v1/proxies."""
        import httpx

        fixture_path = _FIXTURES_DIR / "mcp_proxy_registration.json"
        assert fixture_path.is_file(), (
            "tests/fixtures/mcp_proxy_registration.json not found. Run: make generate-data"
        )
        payload = json.loads(fixture_path.read_text())
        proxy_name = payload["name"]
        base = registry_base_url.rstrip("/")

        httpx.post(base + "/v1/proxies", json=payload, timeout=10.0)

        list_response = httpx.get(base + "/v1/proxies", timeout=10.0)
        assert list_response.status_code == 200

        registered_names = [p.get("name") for p in list_response.json()]
        assert proxy_name in registered_names, (
            f"Proxy '{proxy_name}' not found in /v1/proxies list after registration. "
            f"Found: {registered_names}"
        )

    def test_proxy_transport_is_sse(
        self, registry_base_url: str
    ) -> None:
        """The registered proxy must have transport 'sse' in the registry response."""
        import httpx

        fixture_path = _FIXTURES_DIR / "mcp_proxy_registration.json"
        assert fixture_path.is_file(), (
            "tests/fixtures/mcp_proxy_registration.json not found. Run: make generate-data"
        )
        payload = json.loads(fixture_path.read_text())
        proxy_name = payload["name"]
        base = registry_base_url.rstrip("/")

        httpx.post(base + "/v1/proxies", json=payload, timeout=10.0)

        list_response = httpx.get(base + "/v1/proxies", timeout=10.0)
        assert list_response.status_code == 200

        proxy_record = next(
            (p for p in list_response.json() if p.get("name") == proxy_name),
            None,
        )
        assert proxy_record is not None, f"Proxy '{proxy_name}' not found in registry."
        assert proxy_record.get("transport") == "sse", (
            f"Expected transport 'sse', got: {proxy_record.get('transport')!r}"
        )
