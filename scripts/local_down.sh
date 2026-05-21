#!/usr/bin/env bash
# Planned for: Cluster C1 — Local Environment (MF-E02-T03)
set -euo pipefail

print_usage() {
    echo "Usage: $(basename "$0") [--help]"
    echo ""
    echo "Stop the local Docker Compose stack and remove volumes."
    echo "Planned for: Cluster C1 — Local Environment"
    echo "Ticket: MF-E02-T03"
}

if [[ "${1:-}" == "--help" ]]; then
    print_usage
    exit 0
fi

echo "ERROR: local_down.sh is not yet implemented."
echo "Planned for: Cluster C1 — Local Environment (MF-E02-T03)"
echo "See doc/Plan.md for implementation details."
exit 1
