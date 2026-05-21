#!/usr/bin/env python3
"""Generate deterministic synthetic test data fixtures for MCP Farm tests.

Produces three JSON fixture files consumed by the test suite:
  tests/fixtures/mcp_proxy_registration.json
  tests/fixtures/virtual_server_definition.json
  tests/fixtures/tool_invocation_request.json

All data is generated with a fixed seed (default: 42) so every run produces
identical output. The seed can be overridden with --seed for exploratory use,
but the committed fixtures are always generated with seed 42.

Usage:
  python scripts/generate_synthetic_data.py
  python scripts/generate_synthetic_data.py --seed 42
  python scripts/generate_synthetic_data.py --help
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent
_FIXTURES_DIR = _REPO_ROOT / "tests" / "fixtures"
_DEFAULT_SEED = 42


def _build_mcp_proxy_registration(fake: object) -> dict:
    """Synthetic MCP proxy registration payload (GitLab-like structure)."""
    import faker as faker_module
    f: faker_module.Faker = fake  # type: ignore[assignment]
    return {
        "name": "test-gitlab-proxy",
        "description": f.sentence(nb_words=8),
        "url": f"https://gitlab.{f.domain_name()}/api/mcp/v1",
        "transport": "sse",
        "auth": {
            "type": "oauth2",
            "token_endpoint": f"https://gitlab.{f.domain_name()}/oauth/token",
            "client_id": f.uuid4(),
            "scopes": ["read_api", "read_repository"],
        },
        "metadata": {
            "created_by": f.user_name(),
            "purpose": "integration-test",
        },
    }


def _build_virtual_server_definition(virtual_server_name: str, fake: object) -> dict:
    """Synthetic virtual server definition with two tool entries."""
    import faker as faker_module
    f: faker_module.Faker = fake  # type: ignore[assignment]
    return {
        "name": virtual_server_name,
        "description": f.sentence(nb_words=10),
        "tools": [
            {
                "name": "tool-alpha",
                "description": f.sentence(nb_words=12),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": f.sentence(nb_words=6),
                        }
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "tool-beta",
                "description": f.sentence(nb_words=12),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "entity_id": {
                            "type": "string",
                            "format": "uuid",
                            "description": f.sentence(nb_words=6),
                        }
                    },
                    "required": ["entity_id"],
                },
            },
        ],
    }


def _build_tool_invocation_request(virtual_server_name: str, fake: object) -> dict:
    """Synthetic tool invocation request body for tool-alpha."""
    import faker as faker_module
    f: faker_module.Faker = fake  # type: ignore[assignment]
    return {
        "server": virtual_server_name,
        "tool": "tool-alpha",
        "parameters": {
            "query": f.sentence(nb_words=7),
        },
        "metadata": {
            "request_id": f.uuid4(),
            "caller": f.user_name(),
        },
    }


def generate(seed: int = _DEFAULT_SEED) -> None:
    from faker import Faker

    fake = Faker()
    fake.seed_instance(seed)

    virtual_server_name = os.environ.get("VIRTUAL_SERVER_NAME", "test-virtual-server")

    _FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

    fixtures: list[tuple[str, dict]] = [
        ("mcp_proxy_registration.json", _build_mcp_proxy_registration(fake)),
        (
            "virtual_server_definition.json",
            _build_virtual_server_definition(virtual_server_name, fake),
        ),
        ("tool_invocation_request.json", _build_tool_invocation_request(virtual_server_name, fake)),
    ]

    for filename, data in fixtures:
        path = _FIXTURES_DIR / filename
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        print(f"  Written: {path.relative_to(_REPO_ROOT)}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=int(os.environ.get("TEST_SYNTHETIC_DATA_SEED", _DEFAULT_SEED)),
        help=f"Random seed for deterministic generation (default: {_DEFAULT_SEED})",
    )
    args = parser.parse_args()

    print(f"--- MCP Farm: generate-data (seed={args.seed}) ---")
    print()

    generate(seed=args.seed)

    print()
    print("Fixtures generated. Run tests with: make test CLUSTER=c1")


if __name__ == "__main__":
    main()
