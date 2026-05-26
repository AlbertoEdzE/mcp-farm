#!/usr/bin/env python3
"""Create a virtual server in ContextForge.

Reads a virtual server definition from a JSON fixture file, logs in to
ContextForge to obtain a JWT Bearer token, then POSTs to POST /servers.

Q1 resolved 2026-05-25: endpoint is POST /servers (not /v1/virtual-servers).
Auth required: Bearer JWT obtained from POST /auth/login.
Prerequisite: register-proxy must run first (make register-proxy).

Usage:
  python scripts/create_virtual_server.py
  python scripts/create_virtual_server.py --fixture tests/fixtures/virtual_server_definition.json
  python scripts/create_virtual_server.py --gateway-url http://localhost:4444
  python scripts/create_virtual_server.py --help
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent
_DEFAULT_FIXTURE = _REPO_ROOT / "tests" / "fixtures" / "virtual_server_definition.json"
_DEFAULT_GATEWAY_URL = "http://localhost:4444"
_SERVERS_ENDPOINT = "/servers"
_LOGIN_ENDPOINT = "/auth/login"


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
        return

    if not _which("kubectl"):
        return

    print(f"  Port-forward not active — starting kubectl port-forward svc/contextforge-svc {port}:{port} -n mcp-farm")
    proc = subprocess.Popen(
        ["kubectl", "port-forward", "svc/contextforge-svc", f"{port}:{port}", "-n", "mcp-farm"],
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
        print("Ensure port-forward is active: kubectl port-forward svc/contextforge-svc 4444:4444 -n mcp-farm", file=sys.stderr)
        sys.exit(1)

    if response.status_code != 200:
        print(f"ERROR: Login failed (HTTP {response.status_code}): {response.text}", file=sys.stderr)
        sys.exit(1)

    token = response.json().get("access_token") or response.json().get("token")
    if not token:
        print(f"ERROR: No token in login response: {response.text}", file=sys.stderr)
        sys.exit(1)
    return token


def create(fixture_path: Path, gateway_url: str, email: str, password: str) -> None:
    import httpx

    if not fixture_path.is_file():
        print(f"ERROR: Fixture file not found: {fixture_path}", file=sys.stderr)
        print("Run: make generate-data", file=sys.stderr)
        sys.exit(1)

    raw = json.loads(fixture_path.read_text())

    # Map fixture format to ContextForge ServerCreate schema.
    # POST /servers wraps the server object under a "server" key.
    # Tools are registered separately and linked by ID — not included at creation time.
    payload = {
        "server": {
            "name": raw["name"],
            "description": raw.get("description"),
        }
    }

    token = _login(gateway_url, email, password)
    headers = {"Authorization": f"Bearer {token}"}
    url = gateway_url.rstrip("/") + _SERVERS_ENDPOINT

    print(f"Creating virtual server '{payload['name']}' at {url}")
    try:
        response = httpx.post(url, json=payload, headers=headers, timeout=30.0)
    except httpx.ConnectError as exc:
        print(f"ERROR: Could not connect to ContextForge at {url}: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"HTTP {response.status_code}")

    if response.status_code in (200, 201):
        print(json.dumps(response.json(), indent=2))
    elif response.status_code == 422:
        print(f"ERROR: Validation error — check fixture payload.", file=sys.stderr)
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
        help=f"Path to virtual server definition JSON fixture (default: {_DEFAULT_FIXTURE.relative_to(_REPO_ROOT)})",
    )
    parser.add_argument(
        "--gateway-url",
        default=os.environ.get("TEST_GATEWAY_BASE_URL", _DEFAULT_GATEWAY_URL),
        help=f"ContextForge base URL (default: {_DEFAULT_GATEWAY_URL})",
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

    print("--- MCP Farm: create-virtual-server ---")
    print()
    create(
        fixture_path=args.fixture,
        gateway_url=args.gateway_url,
        email=args.email,
        password=args.password,
    )
    print()
    print("Done. Run 'make test CLUSTER=c5' to validate.")


if __name__ == "__main__":
    main()
