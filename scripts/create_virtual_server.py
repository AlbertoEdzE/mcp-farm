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


def _login(gateway_url: str, email: str, password: str) -> str:
    import httpx

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
    # ServerCreate expects name, description, and optionally tags.
    # Tools are registered separately and linked by ID — not included at creation time.
    payload = {
        "name": raw["name"],
        "description": raw.get("description"),
        "tags": ["mcp-farm", "test"],
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
