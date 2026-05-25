#!/usr/bin/env bash
# Provision GKE cluster, Cloud SQL (PostgreSQL 15), and Memorystore (Redis 7).
#
# Usage:
#   ./scripts/gke_provision.sh [--help]
#
# Prerequisites:
#   - gcloud CLI installed and authenticated (gcloud auth login)
#   - kubectl installed
#   - .env populated with all required variables (see below)
#   - Q2 resolved: GCP_PROJECT_ID set to the target sandbox project
#   - Q6 resolved: GKE_NODE_MACHINE_TYPE and GKE_NODE_COUNT confirmed by Lakshman
#
# Required environment variables (from .env):
#   GCP_PROJECT_ID, GCP_REGION, GCP_ZONE,
#   GKE_CLUSTER_NAME, GKE_NAMESPACE, GKE_NODE_MACHINE_TYPE, GKE_NODE_COUNT,
#   CLOUDSQL_INSTANCE_NAME, CLOUDSQL_DATABASE_NAME,
#   MEMORYSTORE_INSTANCE_NAME
#
# This script is idempotent: re-running after partial failure will skip
# resources that already exist.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

print_usage() {
    echo "Usage: $(basename "$0") [--help]"
    echo ""
    echo "Provision GKE cluster, Cloud SQL (PostgreSQL 15), and Memorystore (Redis 7) for MCP Farm."
    echo ""
    echo "Prerequisites:"
    echo "  gcloud CLI installed and authenticated: gcloud auth login"
    echo "  kubectl installed"
    echo "  .env populated — copy from .env.example and fill all values"
    echo ""
    echo "Open questions that must be resolved before running:"
    echo "  Q2: GCP_PROJECT_ID — sandbox project ID (Chakri)"
    echo "  Q6: GKE_NODE_MACHINE_TYPE, GKE_NODE_COUNT — approved node config (Lakshman)"
    echo ""
    echo "Run order:"
    echo "  1. ./scripts/gke_provision.sh   (this script)"
    echo "  2. ./scripts/gke_deploy.sh"
    echo "  3. ./scripts/gke_teardown.sh    (when done)"
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

for tool in gcloud kubectl; do
    if ! command -v "${tool}" &>/dev/null; then
        echo "ERROR: '${tool}' is not installed or not on PATH."
        exit 1
    fi
done

# ---------------------------------------------------------------------------
# Pre-flight: required environment variables
# ---------------------------------------------------------------------------

REQUIRED_VARS=(
    GCP_PROJECT_ID
    GCP_REGION
    GCP_ZONE
    GKE_CLUSTER_NAME
    GKE_NAMESPACE
    GKE_NODE_MACHINE_TYPE
    GKE_NODE_COUNT
    CLOUDSQL_INSTANCE_NAME
    CLOUDSQL_DATABASE_NAME
    MEMORYSTORE_INSTANCE_NAME
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

echo "--- MCP Farm: GKE Provision ---"
echo ""
echo "Project : ${GCP_PROJECT_ID}"
echo "Zone    : ${GCP_ZONE}"
echo "Region  : ${GCP_REGION}"
echo "Cluster : ${GKE_CLUSTER_NAME}"
echo ""

# ---------------------------------------------------------------------------
# Set active GCP project
# ---------------------------------------------------------------------------

echo "[1/7] Setting active GCP project..."
gcloud config set project "${GCP_PROJECT_ID}"

# ---------------------------------------------------------------------------
# Enable required GCP APIs
# ---------------------------------------------------------------------------

echo "[2/7] Enabling GCP APIs..."
gcloud services enable \
    container.googleapis.com \
    sqladmin.googleapis.com \
    redis.googleapis.com \
    --project="${GCP_PROJECT_ID}"

# ---------------------------------------------------------------------------
# Create dedicated VPC network (skip if already exists)
# ---------------------------------------------------------------------------

echo "[3/8] Creating VPC network 'mcp-farm-network'..."
if gcloud compute networks describe mcp-farm-network \
       --project="${GCP_PROJECT_ID}" &>/dev/null; then
    echo "  VPC network 'mcp-farm-network' already exists — skipping."
else
    gcloud compute networks create mcp-farm-network \
        --project="${GCP_PROJECT_ID}" \
        --subnet-mode=auto
fi

# ---------------------------------------------------------------------------
# Create GKE cluster (skip if already exists)
# ---------------------------------------------------------------------------

echo "[4/8] Creating GKE cluster '${GKE_CLUSTER_NAME}'..."
if gcloud container clusters describe "${GKE_CLUSTER_NAME}" \
       --zone="${GCP_ZONE}" \
       --project="${GCP_PROJECT_ID}" &>/dev/null; then
    echo "  Cluster '${GKE_CLUSTER_NAME}' already exists — skipping creation."
else
    gcloud container clusters create "${GKE_CLUSTER_NAME}" \
        --project="${GCP_PROJECT_ID}" \
        --zone="${GCP_ZONE}" \
        --machine-type="${GKE_NODE_MACHINE_TYPE}" \
        --num-nodes="${GKE_NODE_COUNT}" \
        --network=mcp-farm-network \
        --enable-ip-alias \
        --no-enable-basic-auth \
        --metadata disable-legacy-endpoints=true
fi

# Configure kubectl context
gcloud container clusters get-credentials "${GKE_CLUSTER_NAME}" \
    --zone="${GCP_ZONE}" \
    --project="${GCP_PROJECT_ID}"

# ---------------------------------------------------------------------------
# Create Cloud SQL PostgreSQL 15 instance (skip if already exists)
# ---------------------------------------------------------------------------

echo "[5/8] Creating Cloud SQL instance '${CLOUDSQL_INSTANCE_NAME}'..."
if gcloud sql instances describe "${CLOUDSQL_INSTANCE_NAME}" \
       --project="${GCP_PROJECT_ID}" &>/dev/null; then
    echo "  Cloud SQL instance '${CLOUDSQL_INSTANCE_NAME}' already exists — skipping creation."
else
    gcloud sql instances create "${CLOUDSQL_INSTANCE_NAME}" \
        --project="${GCP_PROJECT_ID}" \
        --region="${GCP_REGION}" \
        --database-version=POSTGRES_15 \
        --tier=db-f1-micro \
        --storage-type=SSD \
        --storage-size=10GB
fi

echo "[6/8] Creating Cloud SQL database '${CLOUDSQL_DATABASE_NAME}'..."
if gcloud sql databases describe "${CLOUDSQL_DATABASE_NAME}" \
       --instance="${CLOUDSQL_INSTANCE_NAME}" \
       --project="${GCP_PROJECT_ID}" &>/dev/null; then
    echo "  Database '${CLOUDSQL_DATABASE_NAME}' already exists — skipping creation."
else
    gcloud sql databases create "${CLOUDSQL_DATABASE_NAME}" \
        --instance="${CLOUDSQL_INSTANCE_NAME}" \
        --project="${GCP_PROJECT_ID}"
fi

# ---------------------------------------------------------------------------
# Create Memorystore Redis 7 instance (skip if already exists)
# ---------------------------------------------------------------------------

echo "[7/8] Creating Memorystore instance '${MEMORYSTORE_INSTANCE_NAME}'..."
if gcloud redis instances describe "${MEMORYSTORE_INSTANCE_NAME}" \
       --region="${GCP_REGION}" \
       --project="${GCP_PROJECT_ID}" &>/dev/null; then
    echo "  Memorystore instance '${MEMORYSTORE_INSTANCE_NAME}' already exists — skipping creation."
else
    gcloud redis instances create "${MEMORYSTORE_INSTANCE_NAME}" \
        --project="${GCP_PROJECT_ID}" \
        --region="${GCP_REGION}" \
        --size=1 \
        --tier=basic \
        --redis-version=redis_7_0
fi

# ---------------------------------------------------------------------------
# Apply GKE namespace
# ---------------------------------------------------------------------------

echo "[8/8] Applying Kubernetes namespace..."
kubectl apply -f "${REPO_ROOT}/k8s/namespace.yaml"

# ---------------------------------------------------------------------------
# Print post-provision information
# ---------------------------------------------------------------------------

echo ""
echo "--- Provision complete ---"
echo ""
echo "Next steps:"
echo "  1. Retrieve the Cloud SQL private IP:"
echo "       gcloud sql instances describe ${CLOUDSQL_INSTANCE_NAME} --project=${GCP_PROJECT_ID} --format='get(ipAddresses[0].ipAddress)'"
echo "     Update CLOUDSQL_CONNECTION_STRING in .env with the private IP."
echo ""
echo "  2. Retrieve the Memorystore host IP:"
echo "       gcloud redis instances describe ${MEMORYSTORE_INSTANCE_NAME} --region=${GCP_REGION} --project=${GCP_PROJECT_ID} --format='get(host)'"
echo "     Update REDIS_HOST in .env with this IP."
echo ""
echo "  3. Run: ./scripts/gke_deploy.sh"
