#!/usr/bin/env bash
# Write .env with all known values for the GCP Cloud Shell deployment.
# Run once after cloning or pulling on a fresh machine.
#
# Usage:
#   bash scripts/setup_gcp_env.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ENV_FILE="${REPO_ROOT}/.env"

if [[ -f "${ENV_FILE}" ]]; then
    echo "WARNING: .env already exists. Overwriting."
fi

cat > "${ENV_FILE}" << 'ENVEOF'
GCP_PROJECT_ID=x-ai-engineering
GCP_REGION=us-central1
GCP_ZONE=us-central1-a
GKE_CLUSTER_NAME=mcp-farm-sandbox
GKE_NAMESPACE=mcp-farm
GKE_NODE_MACHINE_TYPE=e2-standard-2
GKE_NODE_COUNT=2
CF_IMAGE_URI=ghcr.io/ibm/mcp-context-forge
CF_IMAGE_TAG=latest
CF_GATEWAY_PORT=8080
CF_REGISTRY_PORT=8081
CF_EXPOSE_CONTAINER_PORT=true
CF_GATEWAY_HEALTH_PATH=/health
CF_REGISTRY_HEALTH_PATH=/health
CLOUDSQL_INSTANCE_NAME=mcp-farm-pg
CLOUDSQL_DATABASE_NAME=contextforge
CLOUDSQL_USER=contextforge
CLOUDSQL_PASSWORD=McpFarm2026Secure
CLOUDSQL_CONNECTION_STRING=<pending-post-provision>
MEMORYSTORE_INSTANCE_NAME=mcp-farm-redis
REDIS_HOST=<pending-post-provision>
REDIS_PORT=6379
LOCAL_POSTGRES_PORT=5432
LOCAL_REDIS_PORT=6379
LOCAL_CF_GATEWAY_PORT=8080
LOCAL_CF_REGISTRY_PORT=8081
IBM_ENTITLEMENT_KEY=
GITLAB_MCP_URL=<pending-Q4>
GITLAB_OAUTH_CLIENT_ID=<pending-Q4>
GITLAB_OAUTH_CLIENT_SECRET=<pending-Q4>
VIRTUAL_SERVER_NAME=test-virtual-server
TEST_SYNTHETIC_DATA_SEED=42
TEST_TARGET=gke
TEST_GATEWAY_BASE_URL=http://localhost:8080
TEST_REGISTRY_BASE_URL=http://localhost:8081
ENVEOF

echo ".env written to ${ENV_FILE}"
echo ""
echo "Pending values (fill in after gke-provision completes):"
echo "  CLOUDSQL_CONNECTION_STRING — Cloud SQL private IP"
echo "  REDIS_HOST                 — Memorystore host IP"
echo ""
echo "Pending values (need team input):"
echo "  GITLAB_MCP_URL, GITLAB_OAUTH_CLIENT_ID, GITLAB_OAUTH_CLIENT_SECRET — Q4 (Bala)"
echo ""
echo "Next: make gke-provision"
