#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

print_usage() {
    echo "Usage: $(basename "$0") [--help]"
    echo ""
    echo "Stop the local Docker Compose stack and remove all volumes."
    echo "Idempotent: safe to run when the stack is already stopped."
    echo ""
    echo "Options:"
    echo "  --help  Print this message and exit"
    echo ""
    echo "Note: volumes are removed (-v flag). Local PostgreSQL data is not preserved."
    echo "This ensures a clean state on the next local-up."
}

if [[ "${1:-}" == "--help" ]]; then
    print_usage
    exit 0
fi

echo "--- MCP Farm: local-down ---"
echo ""

cd "$REPO_ROOT"

docker compose down -v 2>&1 || true

echo "Stack stopped. All containers and volumes removed."
