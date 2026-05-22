# MCP Farm — Deployment and Operations Runbook

**Document class:** SDD Phase 1 — Operational Reference  
**Author:** Alberto Hernandez  
**Project:** mcp-farm  
**Date:** 2026-05-21

This document is the authoritative step-by-step guide for reproducing any state of the MCP Farm system from a clean checkout. Every command is listed with its expected output or success condition. Any deviation from the expected output indicates a configuration error or an unresolved open question.

---

## Prerequisites

### Required tools

Verify each tool is available before starting:

```bash
python3 --version   # >= 3.11
docker --version    # >= 24.x
make --version
gcloud --version    # >= 460.x  (GKE deployment only)
kubectl version     # >= 1.29   (GKE deployment only)
```

### Open questions — must be resolved before GKE deployment

The following items are unresolved as of 2026-05-21. Local infrastructure (postgres + redis) runs without them. ContextForge stack and GKE require them.

| ID | Variable(s) | Owner | Required for |
|---|---|---|---|
| Q1 | `CF_IMAGE_URI`, `CF_IMAGE_TAG`, `IBM_ENTITLEMENT_KEY` | Kashyap | ContextForge container start, GKE deploy |
| Q2 | `GCP_PROJECT_ID` | Chakri | GKE provision |
| Q4 | `GITLAB_OAUTH_CLIENT_ID`, `GITLAB_OAUTH_CLIENT_SECRET` | Bala | GitLab proxy registration |
| Q5 | — | Chakri | Secret Manager vs Kubernetes Secrets decision |
| Q6 | `GKE_NODE_MACHINE_TYPE`, `GKE_NODE_COUNT` | Lakshman | GKE cluster creation |

When each question is resolved, populate the corresponding variables in `.env` and re-run the affected steps.

### Environment file

```bash
cp .env.example .env
```

Minimum variables required for local infrastructure (postgres + redis):

```
CLOUDSQL_USER=<your-db-username>
CLOUDSQL_PASSWORD=<your-db-password>
```

All other variables have safe defaults in docker-compose.yml or are guarded by skip logic in the scripts.

---

## Part 1 — Local Environment

### Step 1.1 — Install

```bash
make install
```

Expected: `.venv/` created, all packages installed, `reports/` directory created. No errors.

### Step 1.2 — Generate synthetic test data

```bash
make generate-data
```

Expected output:
```
--- MCP Farm: generate-data (seed=42) ---

  Written: tests/fixtures/mcp_proxy_registration.json
  Written: tests/fixtures/virtual_server_definition.json
  Written: tests/fixtures/tool_invocation_request.json

Fixtures generated. Run tests with: make test CLUSTER=c1
```

### Step 1.3 — Run structural tests (no stack required)

These tests verify repository structure only. They always pass regardless of stack state.

```bash
make test CLUSTER=c0,c1,c2,c3,c4,c5,c6
```

Expected: all structural tests pass, integration tests skip.

### Step 1.4 — Start infrastructure (postgres + redis)

Q1 is not required for this step.

```bash
make local-up -- --infra-only
```

Expected: postgres and redis containers reach `healthy` state.

Verify:

```bash
docker compose ps
```

Expected output (Status column): `healthy` for both postgres and redis.

### Step 1.5 — Verify infrastructure tests pass

```bash
make test CLUSTER=c1
```

Expected: `TestInfrastructureStack` tests pass (postgres accepts connections, redis responds to PING). `TestContextForgeStack` tests skip (Q1 unresolved).

### Step 1.6 — Start full ContextForge stack (requires Q1)

Resolve Q1 first: populate `CF_IMAGE_URI`, `CF_IMAGE_TAG`, `IBM_ENTITLEMENT_KEY` in `.env`.

```bash
make local-up
```

Expected: all three services (contextforge, postgres, redis) reach `healthy` state.

### Step 1.7 — Register the GitLab MCP proxy (requires Q4)

Resolve Q4 first: populate `GITLAB_MCP_URL`, `GITLAB_OAUTH_CLIENT_ID`, `GITLAB_OAUTH_CLIENT_SECRET` in `.env`.

```bash
make register-proxy
```

Expected:
```
--- MCP Farm: register-proxy ---

Registering proxy 'test-gitlab-proxy' at http://localhost:8081/v1/proxies
HTTP 201
{ ... proxy record ... }

Done. Run 'make test CLUSTER=c4' to validate.
```

### Step 1.8 — Create the virtual server

The GitLab proxy must be registered (Step 1.7) before this step.

```bash
make create-virtual-server
```

Expected:
```
--- MCP Farm: create-virtual-server ---

Creating virtual server 'test-virtual-server' at http://localhost:8081/v1/virtual-servers
HTTP 201
{ ... virtual server record ... }

Done. Run 'make test CLUSTER=c5' to validate.
```

### Step 1.9 — Run the full test suite

```bash
make test
```

Expected: all tests pass (no skips once Q1 and Q4 are resolved and the stack is running).

### Step 1.10 — Stop the local stack

```bash
make local-down
```

Expected: all containers stopped and removed, `postgres_data` volume deleted.

---

## Part 2 — GKE Deployment

### Prerequisites for GKE

All of Q1, Q2, Q4, Q6 must be resolved. Q5 must be confirmed before deciding on secret management approach.

Populate the following in `.env` before running GKE scripts:

```
GCP_PROJECT_ID=<resolved-Q2>
GCP_REGION=<e.g. us-central1>
GCP_ZONE=<e.g. us-central1-a>
GKE_CLUSTER_NAME=mcp-farm-sandbox
GKE_NAMESPACE=mcp-farm
GKE_NODE_MACHINE_TYPE=<resolved-Q6>
GKE_NODE_COUNT=<resolved-Q6>
CF_IMAGE_URI=<resolved-Q1>
CF_IMAGE_TAG=<resolved-Q1>
IBM_ENTITLEMENT_KEY=<resolved-Q1>
CLOUDSQL_USER=<db-username>
CLOUDSQL_PASSWORD=<db-password>
GITLAB_MCP_URL=<resolved-Q4>
GITLAB_OAUTH_CLIENT_ID=<resolved-Q4>
GITLAB_OAUTH_CLIENT_SECRET=<resolved-Q4>
```

### Step 2.1 — Authenticate with GCP

```bash
gcloud auth login
gcloud auth application-default login
```

### Step 2.2 — Provision GKE cluster, Cloud SQL, and Memorystore

```bash
make gke-provision
```

This script is idempotent: re-running after partial failure skips resources that already exist.

Expected final output:
```
--- Provision complete ---

Next steps:
  1. Retrieve the Cloud SQL private IP: ...
  2. Retrieve the Memorystore host IP: ...
  3. Run: ./scripts/gke_deploy.sh
```

### Step 2.3 — Retrieve managed service IPs and update .env

After provisioning, retrieve the private IPs and update `.env`:

```bash
# Cloud SQL private IP
gcloud sql instances describe ${CLOUDSQL_INSTANCE_NAME} \
  --project=${GCP_PROJECT_ID} \
  --format='get(ipAddresses[0].ipAddress)'
# -> update CLOUDSQL_CONNECTION_STRING in .env

# Memorystore Redis host
gcloud redis instances describe ${MEMORYSTORE_INSTANCE_NAME} \
  --region=${GCP_REGION} \
  --project=${GCP_PROJECT_ID} \
  --format='get(host)'
# -> update REDIS_HOST in .env
```

### Step 2.4 — Deploy ContextForge to GKE

```bash
make gke-deploy
```

Expected final output:
```
--- Deploy complete ---

NAME           READY   STATUS    RESTARTS   AGE
contextforge-... 1/1   Running   0          ...
```

### Step 2.5 — Validate the GKE deployment

```bash
kubectl get pods -n mcp-farm
```

Expected: all pods in `Running` state.

```bash
# Port-forward and verify health endpoint
kubectl port-forward svc/contextforge-svc 8080:8080 -n mcp-farm &
curl http://localhost:8080/health
# Expected: HTTP 200

kubectl port-forward svc/contextforge-svc 8081:8081 -n mcp-farm &
curl http://localhost:8081/health
# Expected: HTTP 200
```

### Step 2.6 — Run integration tests against GKE

```bash
TEST_TARGET=gke \
TEST_GATEWAY_BASE_URL=http://localhost:8080 \
TEST_REGISTRY_BASE_URL=http://localhost:8081 \
make test CLUSTER=c2,c3,c4,c5
```

### Step 2.7 — Teardown (when done)

```bash
make gke-teardown
```

This is destructive. All data is deleted. Pass `-- --force` to skip the confirmation prompt.

---

## Part 3 — Troubleshooting

### ContextForge gateway not reachable after `make local-up`

**Root cause:** `CF_EXPOSE_CONTAINER_PORT` is not set to `true`. See ADR-001.

**Check:**
```bash
docker compose exec contextforge env | grep CF_EXPOSE_CONTAINER_PORT
```

Expected: `CF_EXPOSE_CONTAINER_PORT=true`

If missing: verify `.env` has `CF_EXPOSE_CONTAINER_PORT=true` and the docker-compose.yml passes the variable.

### Cloud Run deployment failure (historical)

The team attempted deployment on Cloud Run on 2026-05-20. It failed for two reasons:

1. `CF_EXPOSE_CONTAINER_PORT` was not set — the gateway did not bind its port.
2. Required GCP API was not activated.

GKE is now the only supported deployment target. See ADR-001.

### `require_infra_stack` skips when docker compose is not running

The test fixture checks `docker compose ps` output, not TCP socket availability. If a system-level Redis is running on port 6379, tests will not be incorrectly activated — they require the project's docker compose stack specifically.

### gke_provision.sh exits with "placeholder" error for env vars

Variables with `<...>` values are treated as unresolved placeholders. Populate the relevant variables in `.env` and re-run.

### IBM entitlement key authentication failure on `make gke-deploy`

Verify `IBM_ENTITLEMENT_KEY` in `.env` matches the key issued by IBM for `icr.io`. The pull secret is created for `icr.io` with username `iamapikey`. Resolve Q1 with Kashyap.

---

## Acceptance Criteria Checklist

From `doc/Specify.md` Section 16:

| # | Criterion | Status |
|---|---|---|
| 1 | GKE cluster reachable via kubectl | Pending Q2, Q6 |
| 2 | All ContextForge pods in Running state | Pending Q1, Q2, Q6 |
| 3 | AI Gateway health endpoint returns 200 | Pending Q1 |
| 4 | Config Registry health endpoint returns 200 | Pending Q1 |
| 5 | GET /v1/tools returns non-empty array with GitLab tools | Pending Q1, Q4 |
| 6 | `make test` passes with exit 0 from clean checkout | Structural tests pass now; integration tests pending Q1 |
| 7 | `make install && make gke-deploy` reproduces on second run | Scripts implemented and idempotent |
| 8 | Runbook contains all steps and expected outputs | Done — this document |
| 9 | All open questions (Q1–Q6) resolved | Q3 assumed via ADR-001; Q1, Q2, Q4, Q5, Q6 open |
| 10 | No secret or credential in any committed file | Verified by TestSecurityBaseline in test_c0_foundation.py |
