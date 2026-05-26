#!/usr/bin/env python3
"""Register an MCP gateway (proxy) with ContextForge.

Reads a proxy registration payload from a JSON fixture file, logs in to
ContextForge to obtain a JWT Bearer token, then POSTs to POST /gateways.

Q1 resolved 2026-05-25: endpoint is POST /gateways (not /v1/proxies).
Auth required: Bearer JWT obtained from POST /auth/login.

Usage:
  python scripts/register_proxy.py
  python scripts/register_proxy.py --fixture tests/fixtures/mcp_proxy_registration.json
  python scripts/register_proxy.py --gateway-url http://localhost:4444
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
_GATEWAYS_ENDPOINT = "/gateways"
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


def register(fixture_path: Path, gateway_url: str, email: str, password: str) -> None:
    import httpx

    if not fixture_path.is_file():
        print(f"ERROR: Fixture file not found: {fixture_path}", file=sys.stderr)
        print("Run: make generate-data", file=sys.stderr)
        sys.exit(1)

    raw = json.loads(fixture_path.read_text())

    # Map fixture format to ContextForge GatewayCreate schema.
    # The fixture retains its original structure for test compatibility;
    # the script translates it to what the API actually accepts.
    payload = {
        "name": raw["name"],
        "url": raw["url"],
        "description": raw.get("description"),
        "transport": raw.get("transport", "SSE").upper(),
        "auth_type": raw.get("auth", {}).get("type"),
    }

    token = _login(gateway_url, email, password)
    headers = {"Authorization": f"Bearer {token}"}
    url = gateway_url.rstrip("/") + _GATEWAYS_ENDPOINT

    print(f"Registering gateway '{payload['name']}' at {url}")
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
        help=f"Path to proxy registration JSON fixture (default: {_DEFAULT_FIXTURE.relative_to(_REPO_ROOT)})",
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

    print("--- MCP Farm: register-proxy ---")
    print()
    register(
        fixture_path=args.fixture,
        gateway_url=args.gateway_url,
        email=args.email,
        password=args.password,
    )
    print()
    print("Done. Run 'make test CLUSTER=c4' to validate.")


if __name__ == "__main__":
    main()
