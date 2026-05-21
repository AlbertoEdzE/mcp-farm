#!/usr/bin/env bash
# Destroy the GKE cluster and all managed GCP data resources for MCP Farm.
#
# Usage:
#   ./scripts/gke_teardown.sh [--force] [--help]
#
# WARNING: This script deletes the GKE cluster, Cloud SQL instance,
# and Memorystore instance. Data is not recoverable after deletion.
# Use --force to skip the confirmation prompt (for CI / non-interactive use).
#
# Required environment variables (from .env):
#   GCP_PROJECT_ID, GCP_REGION, GCP_ZONE,
#   GKE_CLUSTER_NAME, GKE_NAMESPACE,
#   CLOUDSQL_INSTANCE_NAME, MEMORYSTORE_INSTANCE_NAME
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

FORCE=false

print_usage() {
    echo "Usage: $(basename "$0") [--force] [--help]"
    echo ""
    echo "Destroy the MCP Farm GKE cluster and all managed GCP resources."
    echo ""
    echo "WARNING: Deletes GKE cluster, Cloud SQL instance, and Memorystore instance."
    echo "         Data cannot be recovered after deletion."
    echo ""
    echo "Options:"
    echo "  --force   Skip the confirmation prompt (for non-interactive/CI use)"
    echo "  --help    Show this message and exit"
}

for arg in "$@"; do
    case "${arg}" in
        --help)   print_usage; exit 0 ;;
        --force)  FORCE=true ;;
        *)
            echo "ERROR: Unknown argument: ${arg}"
            print_usage
            exit 1
            ;;
    esac
done

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
    CLOUDSQL_INSTANCE_NAME
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
    exit 1
fi

# ---------------------------------------------------------------------------
# Confirmation prompt
# ---------------------------------------------------------------------------

echo "--- MCP Farm: GKE Teardown ---"
echo ""
echo "The following resources will be PERMANENTLY DELETED:"
echo "  GKE cluster    : ${GKE_CLUSTER_NAME} (zone: ${GCP_ZONE})"
echo "  Cloud SQL       : ${CLOUDSQL_INSTANCE_NAME}"
echo "  Memorystore     : ${MEMORYSTORE_INSTANCE_NAME} (region: ${GCP_REGION})"
echo "  GCP project     : ${GCP_PROJECT_ID}"
echo ""

if [[ "${FORCE}" == "false" ]]; then
    read -r -p "Type 'yes' to confirm deletion: " confirmation
    if [[ "${confirmation}" != "yes" ]]; then
        echo "Teardown cancelled."
        exit 0
    fi
fi

# ---------------------------------------------------------------------------
# Delete Kubernetes namespace and all resources within it
# ---------------------------------------------------------------------------

echo "[1/4] Deleting Kubernetes namespace '${GKE_NAMESPACE}'..."
if kubectl get namespace "${GKE_NAMESPACE}" &>/dev/null; then
    kubectl delete namespace "${GKE_NAMESPACE}" --wait=true
else
    echo "  Namespace '${GKE_NAMESPACE}' not found — skipping."
fi

# ---------------------------------------------------------------------------
# Delete GKE cluster
# ---------------------------------------------------------------------------

echo "[2/4] Deleting GKE cluster '${GKE_CLUSTER_NAME}'..."
if gcloud container clusters describe "${GKE_CLUSTER_NAME}" \
       --zone="${GCP_ZONE}" \
       --project="${GCP_PROJECT_ID}" &>/dev/null; then
    gcloud container clusters delete "${GKE_CLUSTER_NAME}" \
        --zone="${GCP_ZONE}" \
        --project="${GCP_PROJECT_ID}" \
        --quiet
else
    echo "  Cluster '${GKE_CLUSTER_NAME}' not found — skipping."
fi

# ---------------------------------------------------------------------------
# Delete Cloud SQL instance
# ---------------------------------------------------------------------------

echo "[3/4] Deleting Cloud SQL instance '${CLOUDSQL_INSTANCE_NAME}'..."
if gcloud sql instances describe "${CLOUDSQL_INSTANCE_NAME}" \
       --project="${GCP_PROJECT_ID}" &>/dev/null; then
    gcloud sql instances delete "${CLOUDSQL_INSTANCE_NAME}" \
        --project="${GCP_PROJECT_ID}" \
        --quiet
else
    echo "  Cloud SQL instance '${CLOUDSQL_INSTANCE_NAME}' not found — skipping."
fi

# ---------------------------------------------------------------------------
# Delete Memorystore instance
# ---------------------------------------------------------------------------

echo "[4/4] Deleting Memorystore instance '${MEMORYSTORE_INSTANCE_NAME}'..."
if gcloud redis instances describe "${MEMORYSTORE_INSTANCE_NAME}" \
       --region="${GCP_REGION}" \
       --project="${GCP_PROJECT_ID}" &>/dev/null; then
    gcloud redis instances delete "${MEMORYSTORE_INSTANCE_NAME}" \
        --region="${GCP_REGION}" \
        --project="${GCP_PROJECT_ID}" \
        --quiet
else
    echo "  Memorystore instance '${MEMORYSTORE_INSTANCE_NAME}' not found — skipping."
fi

echo ""
echo "--- Teardown complete ---"
