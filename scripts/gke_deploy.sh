#!/usr/bin/env bash
# Deploy ContextForge to the GKE cluster.
#
# Usage:
#   ./scripts/gke_deploy.sh [--help]
#
# Prerequisites:
#   - ./scripts/gke_provision.sh completed successfully
#   - kubectl context set to the mcp-farm GKE cluster
#   - .env populated with all required variables (see below)
#   - Q1 resolved: CF_IMAGE_URI, CF_IMAGE_TAG, IBM_ENTITLEMENT_KEY confirmed
#   - CLOUDSQL_CONNECTION_STRING and REDIS_HOST updated with post-provision IPs
#
# Required environment variables (from .env):
#   GKE_NAMESPACE,
#   CF_IMAGE_URI, CF_IMAGE_TAG,
#   IBM_ENTITLEMENT_KEY,
#   CLOUDSQL_USER, CLOUDSQL_PASSWORD, CLOUDSQL_CONNECTION_STRING,
#   REDIS_HOST, REDIS_PORT
#
# This script is idempotent: re-running re-applies all manifests and
# rotates secrets to the current .env values.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
K8S_DIR="${REPO_ROOT}/k8s"

print_usage() {
    echo "Usage: $(basename "$0") [--help]"
    echo ""
    echo "Deploy ContextForge Kubernetes manifests and secrets to the GKE cluster."
    echo ""
    echo "Prerequisites:"
    echo "  - gke_provision.sh completed (cluster exists, namespace applied)"
    echo "  - kubectl context set: gcloud container clusters get-credentials <cluster>"
    echo "  - .env populated — copy from .env.example and fill all values"
    echo ""
    echo "Open questions that must be resolved before running:"
    echo "  Q1: CF_IMAGE_URI, CF_IMAGE_TAG, IBM_ENTITLEMENT_KEY (Kashyap / IBM docs)"
    echo ""
    echo "Run order:"
    echo "  1. ./scripts/gke_provision.sh"
    echo "  2. ./scripts/gke_deploy.sh   (this script)"
    echo "  3. ./scripts/gke_teardown.sh (when done)"
}

if [[ "${1:-}" == "--help" ]]; then
    print_usage
    exit 0
fi

# ---------------------------------------------------------------------------
# Load .env
# ---------------------------------------------------------------------------

ENV_FILE="${REPO_ROOT}/.env"
if [[ ! -f "${ENV_FILE}" ]]; then
    echo "ERROR: .env not found at ${ENV_FILE}"
    echo "Copy .env.example to .env and populate all values."
    exit 1
fi
# shellcheck source=/dev/null
set -a; source "${ENV_FILE}"; set +a

# ---------------------------------------------------------------------------
# Pre-flight: required tools
# ---------------------------------------------------------------------------

for tool in kubectl gcloud; do
    if ! command -v "${tool}" &>/dev/null; then
        echo "ERROR: '${tool}' is not installed or not on PATH."
        exit 1
    fi
done

# ---------------------------------------------------------------------------
# Pre-flight: required environment variables
# ---------------------------------------------------------------------------

REQUIRED_VARS=(
    GKE_NAMESPACE
    CF_IMAGE_URI
    CF_IMAGE_TAG
    CLOUDSQL_USER
    CLOUDSQL_PASSWORD
    CLOUDSQL_DATABASE_NAME
    CLOUDSQL_CONNECTION_STRING
    REDIS_HOST
    REDIS_PORT
)

missing_vars=()
for var in "${REQUIRED_VARS[@]}"; do
    val="${!var:-}"
    if [[ -z "${val}" || "${val}" == \<* ]]; then
        missing_vars+=("${var}")
    fi
done

if [[ ${#missing_vars[@]} -gt 0 ]]; then
    echo "ERROR: The following environment variables are unset or still contain placeholders:"
    for var in "${missing_vars[@]}"; do
        echo "  ${var}=${!var:-<unset>}"
    done
    echo ""
    echo "Populate .env and re-run. See doc/Specify.md Section 15 for open questions."
    exit 1
fi

echo "--- MCP Farm: GKE Deploy ---"
echo ""
echo "Namespace : ${GKE_NAMESPACE}"
echo "Image     : ${CF_IMAGE_URI}:${CF_IMAGE_TAG}"
echo ""

# ---------------------------------------------------------------------------
# Verify kubectl context points to the correct cluster
# ---------------------------------------------------------------------------

current_context="$(kubectl config current-context 2>/dev/null || echo '')"
echo "kubectl context: ${current_context}"
echo ""

# ---------------------------------------------------------------------------
# Apply namespace (idempotent)
# ---------------------------------------------------------------------------

echo "[1/7] Applying namespace..."
kubectl apply -f "${K8S_DIR}/namespace.yaml"

# ---------------------------------------------------------------------------
# Create image pull secret for IBM Container Registry (idempotent)
# ---------------------------------------------------------------------------

echo "[2/7] Image pull secret (optional — ghcr.io image is public)..."
if [[ -n "${IBM_ENTITLEMENT_KEY:-}" && "${IBM_ENTITLEMENT_KEY:-}" != \<* ]]; then
    kubectl create secret docker-registry ibm-entitlement-key \
        --docker-server=ghcr.io \
        --docker-username=ibm \
        --docker-password="${IBM_ENTITLEMENT_KEY}" \
        --namespace="${GKE_NAMESPACE}" \
        --dry-run=client -o yaml | kubectl apply -f -
else
    echo "  IBM_ENTITLEMENT_KEY not set — skipping (public image requires no credentials)."
fi

# ---------------------------------------------------------------------------
# Create database credentials secret (idempotent)
# ---------------------------------------------------------------------------

echo "[3/7] Creating database credentials secret..."
# ContextForge uses psycopg3 (psycopg[c,binary]) — URL scheme must be postgresql+psycopg://.
# Using postgresql+asyncpg:// or postgresql:// will fail — asyncpg is not installed.
# CLOUDSQL_CONNECTION_STRING is "<host>:5432/<dbname>" set by gke_provision.sh.
CLOUDSQL_IP="${CLOUDSQL_CONNECTION_STRING%%:*}"
DATABASE_URL="postgresql+psycopg://${CLOUDSQL_USER}:${CLOUDSQL_PASSWORD}@${CLOUDSQL_IP}:5432/${CLOUDSQL_DATABASE_NAME}"
kubectl create secret generic contextforge-db-credentials \
    --from-literal=DATABASE_URL="${DATABASE_URL}" \
    --namespace="${GKE_NAMESPACE}" \
    --dry-run=client -o yaml | kubectl apply -f -

# ---------------------------------------------------------------------------
# Create Redis credentials secret (idempotent)
# ---------------------------------------------------------------------------

echo "[4/7] Creating Redis credentials secret..."
# ContextForge expects REDIS_URL in redis:// URI format.
REDIS_URL="redis://${REDIS_HOST}:${REDIS_PORT}/0"
kubectl create secret generic contextforge-redis-credentials \
    --from-literal=REDIS_URL="${REDIS_URL}" \
    --namespace="${GKE_NAMESPACE}" \
    --dry-run=client -o yaml | kubectl apply -f -

# ---------------------------------------------------------------------------
# Apply Kubernetes manifests
# ---------------------------------------------------------------------------

echo "[5/8] Applying Kubernetes manifests..."
kubectl apply -f "${K8S_DIR}/configmap.yaml"
kubectl apply -f "${K8S_DIR}/deployment.yaml"
kubectl apply -f "${K8S_DIR}/service.yaml"
kubectl apply -f "${K8S_DIR}/ingress.yaml"
# Force a rollout so the pod picks up any configmap changes even when the
# image tag has not changed (kubectl set image is a no-op in that case).
kubectl rollout restart deployment/contextforge --namespace="${GKE_NAMESPACE}"

# ---------------------------------------------------------------------------
# Deploy demo MCP server (used by register-proxy when GITLAB_MCP_URL is unset)
# ---------------------------------------------------------------------------

echo "[6/8] Deploying demo MCP server (mcp-demo-svc)..."
kubectl apply -f "${K8S_DIR}/mcp-demo-server.yaml"

# ---------------------------------------------------------------------------
# Patch the deployment with the real image URI
# ---------------------------------------------------------------------------

echo "[7/8] Patching deployment image to ${CF_IMAGE_URI}:${CF_IMAGE_TAG}..."
kubectl set image deployment/contextforge \
    contextforge="${CF_IMAGE_URI}:${CF_IMAGE_TAG}" \
    --namespace="${GKE_NAMESPACE}"

# ---------------------------------------------------------------------------
# Wait for both deployments to be ready
# ---------------------------------------------------------------------------

echo "[8/8] Waiting for rollouts (timeout 300s)..."
kubectl rollout status deployment/contextforge \
    --namespace="${GKE_NAMESPACE}" \
    --timeout=300s
kubectl rollout status deployment/mcp-demo-server \
    --namespace="${GKE_NAMESPACE}" \
    --timeout=300s

# ---------------------------------------------------------------------------
# Print post-deploy status
# ---------------------------------------------------------------------------

echo ""
echo "--- Deploy complete ---"
echo ""
kubectl get pods --namespace="${GKE_NAMESPACE}"
echo ""
echo "Next steps:"
echo "  Port-forward and verify health:"
echo "    kubectl port-forward svc/contextforge-svc 4444:4444 -n ${GKE_NAMESPACE} &"
echo "    curl http://localhost:4444/health"
echo ""
echo "  Register proxy and create virtual server:"
echo "    make register-proxy"
echo "    make create-virtual-server"
echo ""
echo "  Run integration tests:"
echo "    TEST_TARGET=gke make test CLUSTER=c2,c3"
