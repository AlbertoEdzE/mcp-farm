#!/usr/bin/env python3
"""Create a virtual server in the ContextForge Config Registry.

Reads a virtual server definition from a JSON fixture file and POSTs it
to the ContextForge Config Registry API. The assumed endpoint is
POST /v1/virtual-servers.

Prerequisites:
  The GitLab MCP proxy must already be registered: make register-proxy

This endpoint and its exact path are unconfirmed until Q1 (CF_IMAGE_URI) is
resolved and the IBM ContextForge API documentation is reviewed.

Usage:
  python scripts/create_virtual_server.py
  python scripts/create_virtual_server.py --fixture tests/fixtures/virtual_server_definition.json
  python scripts/create_virtual_server.py --registry-url http://localhost:8081
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
_DEFAULT_REGISTRY_URL = "http://localhost:8081"
_VIRTUAL_SERVER_ENDPOINT = "/v1/virtual-servers"


def create(fixture_path: Path, registry_url: str) -> None:
    import httpx

    if not fixture_path.is_file():
        print(f"ERROR: Fixture file not found: {fixture_path}", file=sys.stderr)
        print("Run: make generate-data", file=sys.stderr)
        sys.exit(1)

    payload = json.loads(fixture_path.read_text())
    url = registry_url.rstrip("/") + _VIRTUAL_SERVER_ENDPOINT

    print(f"Creating virtual server '{payload.get('name')}' at {url}")

    try:
        response = httpx.post(url, json=payload, timeout=10.0)
    except httpx.ConnectError as exc:
        print(f"ERROR: Could not connect to Config Registry at {url}: {exc}", file=sys.stderr)
        print("Ensure the ContextForge stack is running: make local-up", file=sys.stderr)
        sys.exit(1)

    print(f"HTTP {response.status_code}")

    if response.status_code in (200, 201):
        print(json.dumps(response.json(), indent=2))
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
        "--registry-url",
        default=os.environ.get("TEST_REGISTRY_BASE_URL", _DEFAULT_REGISTRY_URL),
        help=f"ContextForge Config Registry base URL (default: {_DEFAULT_REGISTRY_URL})",
    )
    args = parser.parse_args()

    print("--- MCP Farm: create-virtual-server ---")
    print()
    create(fixture_path=args.fixture, registry_url=args.registry_url)
    print()
    print("Done. Run 'make test CLUSTER=c5' to validate.")


if __name__ == "__main__":
    main()
