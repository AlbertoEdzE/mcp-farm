#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
VENV_DIR="$REPO_ROOT/.venv"

print_usage() {
    echo "Usage: $(basename "$0") [--help]"
    echo ""
    echo "Check system prerequisites and install the Python virtual environment."
    echo "Idempotent: safe to run multiple times."
    echo ""
    echo "Options:"
    echo "  --help    Print this message and exit"
    echo ""
    echo "Required system tools: docker, python3, make"
    echo "Optional system tools: kubectl, gcloud (required for GKE clusters)"
}

if [[ "${1:-}" == "--help" ]]; then
    print_usage
    exit 0
fi

echo "--- MCP Farm: install ---"
echo ""

# Check required system tools
REQUIRED_TOOLS=(docker python3 make)
OPTIONAL_TOOLS=(kubectl gcloud)
MISSING_REQUIRED=()

echo "Checking required tools:"
for tool in "${REQUIRED_TOOLS[@]}"; do
    if command -v "$tool" &>/dev/null; then
        echo "  OK  $tool ($(command -v "$tool"))"
    else
        echo "  MISSING  $tool"
        MISSING_REQUIRED+=("$tool")
    fi
done

echo ""
echo "Checking optional tools (required for GKE deployment):"
for tool in "${OPTIONAL_TOOLS[@]}"; do
    if command -v "$tool" &>/dev/null; then
        echo "  OK  $tool ($(command -v "$tool"))"
    else
        echo "  WARN  $tool not found — install before running gke-provision or gke-deploy"
    fi
done

echo ""
echo "Checking docker compose:"
if docker compose version &>/dev/null 2>&1; then
    echo "  OK  docker compose ($(docker compose version --short 2>/dev/null || echo 'version unknown'))"
else
    echo "  WARN  docker compose not found — required for local-up"
fi

if [[ ${#MISSING_REQUIRED[@]} -gt 0 ]]; then
    echo ""
    echo "ERROR: The following required tools are not installed:"
    for t in "${MISSING_REQUIRED[@]}"; do
        echo "  - $t"
    done
    echo ""
    echo "Install the missing tools and re-run this script."
    exit 1
fi

# Create or update Python virtual environment
echo ""
echo "Setting up Python virtual environment: $VENV_DIR"

if [[ -d "$VENV_DIR" ]]; then
    echo "  Virtual environment already exists — updating packages."
else
    python3 -m venv "$VENV_DIR"
    echo "  Created virtual environment."
fi

"$VENV_DIR/bin/pip" install --quiet --upgrade pip
"$VENV_DIR/bin/pip" install --quiet -r "$REPO_ROOT/requirements-dev.txt"
echo "  Installed requirements-dev.txt."

# Ensure reports directory exists
mkdir -p "$REPO_ROOT/reports"
echo "  reports/ directory ready."

echo ""
echo "--- Installation complete ---"
echo ""
echo "Next steps:"
echo "  1. Copy .env.example to .env and populate all placeholder values."
echo "  2. Activate the virtual environment:"
echo "       source .venv/bin/activate"
echo "  3. Verify the C0 test suite passes:"
echo "       make test CLUSTER=c0"
echo "  4. Start the local stack (after completing Cluster C1):"
echo "       make local-up"
