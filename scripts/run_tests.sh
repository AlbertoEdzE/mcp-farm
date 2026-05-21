#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
CLUSTER=""

print_usage() {
    echo "Usage: $(basename "$0") [--cluster <ids>] [--help]"
    echo ""
    echo "Run the MCP Farm test suite using pytest."
    echo ""
    echo "Options:"
    echo "  --cluster <ids>  Comma-separated cluster IDs to filter, e.g. c0 or c0,c1,c2"
    echo "  --help           Print this message and exit"
    echo ""
    echo "Examples:"
    echo "  $(basename "$0")                       Run all tests"
    echo "  $(basename "$0") --cluster c0          Run Cluster 0 tests only"
    echo "  $(basename "$0") --cluster c0,c1,c2    Run Clusters 0, 1, and 2"
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --cluster)
            CLUSTER="$2"
            shift 2
            ;;
        --help)
            print_usage
            exit 0
            ;;
        *)
            echo "ERROR: Unknown argument: $1"
            print_usage
            exit 1
            ;;
    esac
done

# Load .env if present (does not override existing environment variables)
if [[ -f "$REPO_ROOT/.env" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "$REPO_ROOT/.env"
    set +a
fi

# Activate virtual environment if not already active
if [[ -z "${VIRTUAL_ENV:-}" ]] && [[ -d "$REPO_ROOT/.venv" ]]; then
    # shellcheck disable=SC1091
    source "$REPO_ROOT/.venv/bin/activate"
fi

mkdir -p "$REPO_ROOT/reports"

PYTEST_ARGS=(
    "--tb=short"
    "--junit-xml=$REPO_ROOT/reports/test-results.xml"
    "-v"
)

if [[ -n "$CLUSTER" ]]; then
    TEST_FILES=()
    IFS=',' read -ra CLUSTER_IDS <<< "$CLUSTER"
    for c in "${CLUSTER_IDS[@]}"; do
        c_trimmed="${c// /}"
        while IFS= read -r -d '' match; do
            TEST_FILES+=("$match")
        done < <(find "$REPO_ROOT/tests" -name "test_${c_trimmed}_*.py" -print0 2>/dev/null)
    done

    if [[ ${#TEST_FILES[@]} -eq 0 ]]; then
        echo "ERROR: No test files found for cluster filter: $CLUSTER"
        echo "Available test files:"
        find "$REPO_ROOT/tests" -name "test_c*.py" | sort
        exit 1
    fi

    PYTEST_ARGS+=("${TEST_FILES[@]}")
else
    PYTEST_ARGS+=("$REPO_ROOT/tests/")
fi

echo "--- MCP Farm: test ---"
echo "Cluster filter : ${CLUSTER:-all}"
echo "Report output  : $REPO_ROOT/reports/test-results.xml"
echo ""

python -m pytest "${PYTEST_ARGS[@]}"
