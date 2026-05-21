#!/usr/bin/env python3
"""Generate synthetic test data fixtures for MCP Farm tests.

Planned for: Cluster C1 — Local Environment (MF-E02-T04)

When implemented, this script produces:
  tests/fixtures/mcp_proxy_registration.json
  tests/fixtures/virtual_server_definition.json
  tests/fixtures/tool_invocation_request.json

All data is generated deterministically using faker with a fixed seed.
"""
import argparse
import sys


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate synthetic test data fixtures for MCP Farm tests.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Planned for: Cluster C1 — Local Environment (MF-E02-T04)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for deterministic data generation (default: 42)",
    )
    args = parser.parse_args()

    print("ERROR: generate_synthetic_data.py is not yet implemented.")
    print("Planned for: Cluster C1 — Local Environment (MF-E02-T04)")
    print(f"Seed that will be used: {args.seed}")
    print("See doc/Plan.md for implementation details.")
    sys.exit(1)


if __name__ == "__main__":
    main()
