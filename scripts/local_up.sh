#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
INFRA_ONLY=false

print_usage() {
    echo "Usage: $(basename "$0") [--infra-only] [--help]"
    echo ""
    echo "Start the local Docker Compose stack (ContextForge + PostgreSQL + Redis)."
    echo "Idempotent: safe to run when the stack is already running."
    echo ""
    echo "Options:"
    echo "  --infra-only  Start only postgres and redis (use when Q1 is not yet resolved)"
    echo "  --help        Print this message and exit"
    echo ""
    echo "Prerequisites:"
    echo "  - .env file populated from .env.example"
    echo "  - Docker daemon running"
    echo "  - CF_IMAGE_URI resolved (Q1) — or use --infra-only"
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --infra-only) INFRA_ONLY=true; shift ;;
        --help) print_usage; exit 0 ;;
        *) echo "ERROR: Unknown argument: $1"; print_usage; exit 1 ;;
    esac
done

# Load .env
if [[ ! -f "$REPO_ROOT/.env" ]]; then
    echo "ERROR: .env file not found at $REPO_ROOT/.env"
    echo "Copy .env.example to .env and populate all values:"
    echo "  cp .env.example .env"
    exit 1
fi

set -a
# shellcheck disable=SC1090
source "$REPO_ROOT/.env"
set +a

# Verify Docker daemon is running
if ! docker info &>/dev/null 2>&1; then
    echo "ERROR: Docker daemon is not running. Start Docker and retry."
    exit 1
fi

# Check required env vars
MISSING_VARS=()
for var in CLOUDSQL_USER CLOUDSQL_PASSWORD CLOUDSQL_DATABASE_NAME; do
    if [[ -z "${!var:-}" ]]; then
        MISSING_VARS+=("$var")
    fi
done
if [[ ${#MISSING_VARS[@]} -gt 0 ]]; then
    echo "ERROR: Required environment variables are not set: ${MISSING_VARS[*]}"
    echo "Populate them in .env."
    exit 1
fi

# Check ContextForge image resolution unless --infra-only
if [[ "$INFRA_ONLY" == "false" ]]; then
    CF_IMAGE_URI="${CF_IMAGE_URI:-}"
    if [[ -z "$CF_IMAGE_URI" || "$CF_IMAGE_URI" == "<"* ]]; then
        echo "WARNING: CF_IMAGE_URI is not resolved (Q1 is open)."
        echo "  Current value: ${CF_IMAGE_URI:-<not set>}"
        echo ""
        echo "To start only postgres and redis (sufficient for infrastructure tests):"
        echo "  scripts/local_up.sh --infra-only"
        echo ""
        echo "To start the full stack, resolve Q1 first and update .env."
        exit 1
    fi
fi

echo "--- MCP Farm: local-up ---"
echo ""

cd "$REPO_ROOT"

if [[ "$INFRA_ONLY" == "true" ]]; then
    echo "Starting infrastructure services only (postgres, redis)..."
    docker compose up -d --wait postgres redis
    echo ""
    echo "Infrastructure services running:"
    echo "  PostgreSQL : localhost:${LOCAL_POSTGRES_PORT:-5432}"
    echo "  Redis      : localhost:${LOCAL_REDIS_PORT:-6379}"
    echo ""
    echo "NOTE: ContextForge not started (--infra-only mode)."
    echo "Resolve Q1 (CF_IMAGE_URI) and run without --infra-only for the full stack."
else
    echo "Starting full stack (contextforge, postgres, redis)..."
    docker compose up -d --wait
    echo ""
    echo "All services healthy."
    echo ""
    echo "  AI Gateway  : http://localhost:${LOCAL_CF_GATEWAY_PORT:-8080}"
    echo "  Registry    : http://localhost:${LOCAL_CF_REGISTRY_PORT:-8081}"
    echo "  PostgreSQL  : localhost:${LOCAL_POSTGRES_PORT:-5432}"
    echo "  Redis       : localhost:${LOCAL_REDIS_PORT:-6379}"
    echo ""
    echo "Run tests: make test CLUSTER=c1"
fi
