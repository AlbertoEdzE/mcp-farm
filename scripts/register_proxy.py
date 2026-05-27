#!/usr/bin/env python3
"""Register an MCP gateway (proxy) with ContextForge.

Reads a proxy registration payload from a JSON fixture file, logs in to
ContextForge to obtain a JWT Bearer token, then POSTs to POST /gateways.

Q1 resolved 2026-05-25: endpoint is POST /gateways (not /v1/proxies).
Auth required: Bearer JWT obtained from POST /auth/login.

URL resolution order (first non-placeholder value wins):
  1. --mcp-url CLI argument
  2. GITLAB_MCP_URL environment variable
  3. url field in the fixture file
  4. http://httpbin.org/ (demo fallback when Q4 is still pending)

Usage:
  python scripts/register_proxy.py
  python scripts/register_proxy.py --fixture tests/fixtures/mcp_proxy_registration.json
  python scripts/register_proxy.py --gateway-url http://localhost:4444
  python scripts/register_proxy.py --mcp-url https://gitlab.example.com/api/mcp/v1
  python scripts/register_proxy.py --help
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent
_DEFAULT_FIXTURE = _REPO_ROOT / "tests" / "fixtures" / "mcp_proxy_registration.json"
_DEFAULT_GATEWAY_URL = "http://localhost:4444"
_DEMO_MCP_URL = "http://mcp-demo-svc.mcp-farm.svc.cluster.local:9000/sse"
_GATEWAYS_ENDPOINT = "/gateways"
_LOGIN_ENDPOINT = "/auth/login"


def _is_placeholder(value: str | None) -> bool:
    """Return True if value is unset, empty, or a <...> template placeholder."""
    return not value or value.startswith("<")


def _ensure_port_forward(gateway_url: str) -> None:
    """Start kubectl port-forward in the background if the gateway is unreachable.

    Only acts when gateway_url targets localhost/127.0.0.1 and the port is
    not yet open.  Blocks until the port accepts connections (up to 20s).
    """
    import socket
    import subprocess
    import time
    from urllib.parse import urlparse

    parsed = urlparse(gateway_url)
    host = parsed.hostname or "localhost"
    port = parsed.port or 4444

    if host not in ("localhost", "127.0.0.1"):
        return

    def _port_open() -> bool:
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except OSError:
            return False

    if _port_open():
        return  # Already reachable — nothing to do.

    if not _which("kubectl"):
        return  # kubectl not available — let the caller surface the error.

    print(f"  Port-forward not active — starting kubectl port-forward svc/contextforge-svc {port}:80 -n mcp-farm")
    proc = subprocess.Popen(
        ["kubectl", "port-forward", "svc/contextforge-svc", f"{port}:80", "-n", "mcp-farm"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    import atexit
    atexit.register(proc.terminate)

    deadline = time.time() + 20
    while time.time() < deadline:
        if _port_open():
            print(f"  Port-forward ready on {host}:{port}")
            return
        time.sleep(0.5)

    print("WARNING: Port-forward did not become ready in 20s — continuing anyway.", file=sys.stderr)


def _which(cmd: str) -> bool:
    import shutil
    return shutil.which(cmd) is not None


def _login(gateway_url: str, email: str, password: str) -> str:
    import httpx

    _ensure_port_forward(gateway_url)
    url = gateway_url.rstrip("/") + _LOGIN_ENDPOINT
    try:
        response = httpx.post(
            url,
            json={"email": email, "password": password},
            timeout=10.0,
        )
    except httpx.ConnectError as exc:
        print(f"ERROR: Could not connect to ContextForge at {url}: {exc}", file=sys.stderr)
        print("Ensure port-forward is active: kubectl port-forward svc/contextforge-svc 4444:80 -n mcp-farm", file=sys.stderr)
        sys.exit(1)

    if response.status_code != 200:
        print(f"ERROR: Login failed (HTTP {response.status_code}): {response.text}", file=sys.stderr)
        sys.exit(1)

    token = response.json().get("access_token") or response.json().get("token")
    if not token:
        print(f"ERROR: No token in login response: {response.text}", file=sys.stderr)
        sys.exit(1)
    return token


def register(
    fixture_path: Path,
    gateway_url: str,
    email: str,
    password: str,
    mcp_url: str | None = None,
) -> None:
    import httpx

    if not fixture_path.is_file():
        print(f"ERROR: Fixture file not found: {fixture_path}", file=sys.stderr)
        print("Run: make generate-data", file=sys.stderr)
        sys.exit(1)

    raw = json.loads(fixture_path.read_text())

    # Resolve the MCP server URL.  The fixture url field is always a
    # Faker-generated fake domain that fails ContextForge's SSRF_DNS_FAIL_CLOSED
    # check — it is never used as the registered URL.
    # Priority: --mcp-url arg > GITLAB_MCP_URL env var > demo fallback.
    env_mcp_url = os.environ.get("GITLAB_MCP_URL", "")
    resolved_url = (
        mcp_url if not _is_placeholder(mcp_url)
        else env_mcp_url if not _is_placeholder(env_mcp_url)
        else _DEMO_MCP_URL
    )

    if resolved_url == _DEMO_MCP_URL:
        print(
            "WARNING: GITLAB_MCP_URL is not set — using in-cluster demo MCP server "
            f"({_DEMO_MCP_URL}). Set GITLAB_MCP_URL in .env once Q4 is resolved.",
            file=sys.stderr,
        )

    # ContextForge GatewayCreate auth_type enum: basic | bearer | oauth |
    # authheaders | query_param.  Fixture uses "oauth2"; normalise it.
    raw_auth_type = raw.get("auth", {}).get("type", "")
    auth_type = "oauth" if raw_auth_type == "oauth2" else raw_auth_type or None

    # Map fixture format to ContextForge GatewayCreate schema.
    # The fixture retains its original structure for test compatibility;
    # the script translates it to what the API actually accepts.
    payload = {
        "name": raw["name"],
        "url": resolved_url,
        "description": raw.get("description"),
        "transport": raw.get("transport", "SSE").upper(),
        "auth_type": auth_type,
    }

    token = _login(gateway_url, email, password)
    headers = {"Authorization": f"Bearer {token}"}
    url = gateway_url.rstrip("/") + _GATEWAYS_ENDPOINT

    print(f"Registering gateway '{payload['name']}' at {url}")
    print(f"  MCP server URL : {resolved_url}")
    try:
        response = httpx.post(url, json=payload, headers=headers, timeout=30.0)
    except httpx.ConnectError as exc:
        print(f"ERROR: Could not connect to ContextForge at {url}: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"HTTP {response.status_code}")

    if response.status_code in (200, 201):
        print(json.dumps(response.json(), indent=2))
    elif response.status_code == 422:
        print("ERROR: Validation error — check fixture payload.", file=sys.stderr)
        print(response.text, file=sys.stderr)
        sys.exit(1)
    else:
        print(f"ERROR: Unexpected status {response.status_code}", file=sys.stderr)
        print(response.text, file=sys.stderr)
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--fixture",
        type=Path,
        default=_DEFAULT_FIXTURE,
        help=f"Path to proxy registration JSON fixture (default: {_DEFAULT_FIXTURE.relative_to(_REPO_ROOT)})",
    )
    parser.add_argument(
        "--gateway-url",
        default=os.environ.get("TEST_GATEWAY_BASE_URL", _DEFAULT_GATEWAY_URL),
        help=f"ContextForge base URL (default: {_DEFAULT_GATEWAY_URL})",
    )
    parser.add_argument(
        "--mcp-url",
        default=None,
        help="Override the MCP server URL registered in ContextForge (overrides GITLAB_MCP_URL env var and fixture url field)",
    )
    parser.add_argument(
        "--email",
        default=os.environ.get("CF_ADMIN_EMAIL", "admin@example.com"),
        help="ContextForge admin email (default: admin@example.com)",
    )
    parser.add_argument(
        "--password",
        default=os.environ.get("CF_ADMIN_PASSWORD", "changeme"),
        help="ContextForge admin password (default: changeme)",
    )
    args = parser.parse_args()

    print("--- MCP Farm: register-proxy ---")
    print()
    register(
        fixture_path=args.fixture,
        gateway_url=args.gateway_url,
        email=args.email,
        password=args.password,
        mcp_url=args.mcp_url,
    )
    print()
    print("Done. Run 'make test CLUSTER=c4' to validate.")


if __name__ == "__main__":
    main()
