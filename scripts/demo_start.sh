#!/usr/bin/env bash
# Demo startup: verify the contextforge pod is healthy, start the port-forward,
# and ensure .env holds the correct admin password — all in one command.
#
# Run this every time you open Cloud Shell before starting a demo.
# Safe to re-run — kills any stale port-forward on 8080 before starting a fresh one.
# If CF_ADMIN_PASSWORD in .env is wrong or missing, prompts once and writes the
# correct value so subsequent make targets (create-virtual-server, etc.) work.
#
# Usage:
#   ./scripts/demo_start.sh
#   make demo-start
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ENV_FILE="${REPO_ROOT}/.env"
NAMESPACE="mcp-farm"
LOCAL_PORT="8080"
SERVICE_PORT="80"
SERVICE_NAME="contextforge-svc"

echo "--- MCP Farm Demo Start ---"
echo ""

# ---------------------------------------------------------------------------
# Load .env so cluster name, region, and credentials are available
# ---------------------------------------------------------------------------

if [[ -f "${ENV_FILE}" ]]; then
    set -a; source "${ENV_FILE}"; set +a
fi

CF_ADMIN_EMAIL="${CF_ADMIN_EMAIL:-admin@example.com}"
CF_ADMIN_PASSWORD="${CF_ADMIN_PASSWORD:-changeme}"

# ---------------------------------------------------------------------------
# Pre-flight: kubectl must be configured and cluster reachable
# ---------------------------------------------------------------------------

if ! kubectl cluster-info &>/dev/null; then
    echo "ERROR: kubectl is not configured or the cluster is unreachable."
    echo ""
    echo "Fix: run the following command to restore kubectl context."
    echo "  gcloud container clusters get-credentials ${GKE_CLUSTER_NAME:-mcp-farm-sandbox} \\"
    echo "    --region ${GCP_REGION:-us-central1} --project x-ai-engineering"
    exit 1
fi

# ---------------------------------------------------------------------------
# Check pod readiness
# ---------------------------------------------------------------------------

echo "Checking pod status..."

POD_READY=$(kubectl get pods -n "${NAMESPACE}" -l app=contextforge \
    -o jsonpath='{.items[0].status.containerStatuses[0].ready}' 2>/dev/null || echo "false")

if [[ "${POD_READY}" != "true" ]]; then
    echo "Pod is not Ready yet. Waiting up to 90s..."
    if ! kubectl wait pod -n "${NAMESPACE}" -l app=contextforge \
            --for=condition=Ready --timeout=90s 2>/dev/null; then
        echo ""
        echo "ERROR: Pod did not become Ready within 90s."
        echo ""
        kubectl get pods -n "${NAMESPACE}"
        echo ""
        echo "Diagnose with:"
        echo "  kubectl describe pod -n ${NAMESPACE} -l app=contextforge"
        echo "  kubectl logs -n ${NAMESPACE} -l app=contextforge --tail=40"
        exit 1
    fi
fi

echo "Pod is Running and Ready."
echo ""

# ---------------------------------------------------------------------------
# Kill any stale port-forward on the same port
# ---------------------------------------------------------------------------

if pkill -f "kubectl port-forward.*${LOCAL_PORT}:${SERVICE_PORT}" 2>/dev/null; then
    echo "Stopped stale port-forward. Waiting 2s..."
    sleep 2
fi

# ---------------------------------------------------------------------------
# Start fresh port-forward in background
# ---------------------------------------------------------------------------

echo "Starting port-forward: localhost:${LOCAL_PORT} -> ${SERVICE_NAME}:${SERVICE_PORT} ..."
kubectl port-forward svc/"${SERVICE_NAME}" "${LOCAL_PORT}":"${SERVICE_PORT}" \
    -n "${NAMESPACE}" >"${TMPDIR:-/tmp}/portforward.log" 2>&1 &
PF_PID=$!
sleep 4

# ---------------------------------------------------------------------------
# Verify health endpoint responds
# ---------------------------------------------------------------------------

if curl -sf "http://localhost:${LOCAL_PORT}/health" &>/dev/null; then
    echo "Health check passed (HTTP 200 on /health)."
else
    echo "WARNING: Health check did not respond on port ${LOCAL_PORT}."
    echo "Port-forward log:"
    cat "${TMPDIR:-/tmp}/portforward.log" || true
    echo ""
    echo "The port-forward may still be starting. Wait 10s and try:"
    echo "  curl http://localhost:${LOCAL_PORT}/health"
fi

# ---------------------------------------------------------------------------
# Verify admin credentials — prompt and update .env if wrong
# ---------------------------------------------------------------------------

echo ""
echo "Verifying admin credentials..."

LOGIN_JSON=$(printf '{"email":"%s","password":"%s"}' "${CF_ADMIN_EMAIL}" "${CF_ADMIN_PASSWORD}")
LOGIN_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST "http://localhost:${LOCAL_PORT}/auth/login" \
    -H "Content-Type: application/json" \
    -d "${LOGIN_JSON}" 2>/dev/null || echo "000")

if [[ "${LOGIN_STATUS}" == "200" ]]; then
    echo "Admin credentials verified."
else
    echo ""
    echo "WARNING: CF_ADMIN_PASSWORD in .env did not authenticate (HTTP ${LOGIN_STATUS})."
    echo "Enter the current admin password (input is hidden):"
    read -rs ENTERED_PASSWORD
    echo ""

    VERIFY_JSON=$(printf '{"email":"%s","password":"%s"}' "${CF_ADMIN_EMAIL}" "${ENTERED_PASSWORD}")
    VERIFY_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
        -X POST "http://localhost:${LOCAL_PORT}/auth/login" \
        -H "Content-Type: application/json" \
        -d "${VERIFY_JSON}" 2>/dev/null || echo "000")

    if [[ "${VERIFY_STATUS}" != "200" ]]; then
        echo "ERROR: Password verification failed (HTTP ${VERIFY_STATUS})."
        echo "Re-run 'make demo-start' and try again."
        exit 1
    fi

    CF_ADMIN_PASSWORD="${ENTERED_PASSWORD}"

    if grep -q "^CF_ADMIN_PASSWORD=" "${ENV_FILE}" 2>/dev/null; then
        sed -i "s|^CF_ADMIN_PASSWORD=.*|CF_ADMIN_PASSWORD=${CF_ADMIN_PASSWORD}|" "${ENV_FILE}"
    else
        echo "CF_ADMIN_PASSWORD=${CF_ADMIN_PASSWORD}" >> "${ENV_FILE}"
    fi
    echo ".env updated: CF_ADMIN_PASSWORD written."
fi

# ---------------------------------------------------------------------------
# Print next steps
# ---------------------------------------------------------------------------

echo ""
echo "==========================================="
echo " Admin UI is ready"
echo "==========================================="
echo ""
echo "  1. Click 'Web Preview' in the Cloud Shell toolbar (top-right icon)"
echo "  2. Select 'Preview on port 8080'"
echo "  3. Append /admin to the URL in the browser address bar"
echo "  4. Log in with:"
echo "       Email   : ${CF_ADMIN_EMAIL}"
echo "       Password: ${CF_ADMIN_PASSWORD}"
echo ""
echo "Port-forward PID : ${PF_PID}"
echo "Port-forward log : ${TMPDIR:-/tmp}/portforward.log"
echo ""
echo "To stop the port-forward when done:"
echo "  kill ${PF_PID}"
