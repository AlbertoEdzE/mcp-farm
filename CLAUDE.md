# CLAUDE.md — MCP Farm Continuation Context

Read this file completely before taking any action. It is the authoritative briefing
for any Claude Code session in this repository — local or remote (GCP Cloud Shell).

---

## Project Identity

MCP Farm deploys IBM ContextForge (Apache 2.0, `ghcr.io/ibm/mcp-context-forge:latest`)
on Google Kubernetes Engine as the enterprise MCP gateway for the Baptist Health AI platform.
AI agents connect to port 8080 (AI Gateway) to discover and invoke tools. Administrators
configure the system via port 8081 (Config Registry): registering MCP proxies (GitLab,
Snowflake) and defining virtual servers that scope tool access per agent role.

**GCP project:** `x-ai-engineering` (project number 1030710021223)

---

## Implementation State

All seven clusters are complete. The test suite validates structure and integration.

| Cluster | Epic | Scope | Status |
|---------|------|-------|--------|
| C0 | E01 | Repository structure, env templates, Makefile | Done |
| C1 | E02 | Docker Compose, install scripts, synthetic data | Done |
| C2 | E03 | ContextForge config, health paths, ADR-001 | Done |
| C3 | E04 | GKE provision/deploy/teardown scripts, ADR-002 | Done |
| C4 | E05 | GitLab MCP proxy, OAuth strategy, ADR-003 | Done |
| C5 | E06 | Virtual server access control, ADR-004 | Done |
| C6 | E07 | README, Runbook, documentation tests | Done |

---

## Open Questions

| ID | Variable(s) | Status |
|----|-------------|--------|
| Q1 | CF_IMAGE_URI, CF_IMAGE_TAG | Resolved — `ghcr.io/ibm/mcp-context-forge:latest` |
| Q2 | GCP_PROJECT_ID | Resolved — `x-ai-engineering` |
| Q3 | expose_container_port config key | Assumed — `gateway.expose_container_port: true` (ADR-001) |
| Q4 | GITLAB_OAUTH_CLIENT_ID, GITLAB_OAUTH_CLIENT_SECRET | Pending — confirm with Bala |
| Q5 | Secret Manager vs Kubernetes Secrets | Pending — confirm with Chakri |
| Q6 | GKE_NODE_MACHINE_TYPE, GKE_NODE_COUNT | Pending — confirm with Lakshman |

Before running `make gke-provision`, Q4 and Q6 must be resolved and populated in `.env`.

---

## Non-Negotiable Constraints

These apply to every file, script, test, output, and commit message — no exceptions.

1. No emojis anywhere.
2. No mock objects in tests. Real subsystems or Faker-generated synthetic data only.
3. No hardcoded credentials, hostnames, or environment-specific values in committed files.
4. Sensitive variables in committed files use `<...>` placeholder convention.
5. `.env` is never committed. It is in `.gitignore`.
6. All scripts are idempotent. Re-running after partial failure must not error.
7. One atomic commit per cluster. Format: `type(cN): description`
8. Progressive test suite. All prior cluster tests re-run with each new cluster.
9. Structural tests always run. Integration tests skip gracefully when stack is not running.
10. Faker seed=42 for all synthetic data. Output is deterministic across machines.

---

## Environment Setup (Cloud Shell or Fresh Machine)

```bash
# 1. Clone
git clone https://github.com/AlbertoEdzE/mcp-farm.git
cd mcp-farm

# 2. Create .env — never commit this file
cp .env.example .env

# 3. Populate .env — minimum required for structural tests
#    (ask the operator for Q4 and Q6 values before gke-provision)
#    GCP_REGION, GCP_ZONE
#    GKE_NODE_MACHINE_TYPE, GKE_NODE_COUNT         (Q6 — Lakshman)
#    CLOUDSQL_USER, CLOUDSQL_PASSWORD
#    GITLAB_MCP_URL, GITLAB_OAUTH_CLIENT_ID, GITLAB_OAUTH_CLIENT_SECRET  (Q4 — Bala)

# 4. Install Python virtual environment
make install

# 5. Generate synthetic test fixtures
make generate-data

# 6. Verify structural tests pass (no stack required)
make test CLUSTER=c0,c1,c2,c3,c4,c5,c6
# Expected: all structural tests pass, integration tests skip
```

---

## GKE Deployment Path

Run in this exact order. Each step depends on the previous completing successfully.

```bash
# Step 1 — Provision GKE cluster, Cloud SQL, Memorystore
make gke-provision
# After completion: retrieve Cloud SQL private IP and Memorystore host IP.
# Update CLOUDSQL_CONNECTION_STRING and REDIS_HOST in .env before proceeding.

# Step 2 — Deploy ContextForge to GKE
make gke-deploy
# Verify:
kubectl get pods -n mcp-farm
# Expected: contextforge pod Running, READY 1/1

# Step 3 — Verify health endpoints (port-forward required)
kubectl port-forward svc/contextforge-svc 8080:8080 -n mcp-farm &
kubectl port-forward svc/contextforge-svc 8081:8081 -n mcp-farm &
curl http://localhost:8080/health   # Expected: HTTP 200
curl http://localhost:8081/health   # Expected: HTTP 200

# Step 4 — Register GitLab MCP proxy (requires Q4 resolved)
make register-proxy

# Step 5 — Create virtual server
make create-virtual-server

# Step 6 — Run full test suite and generate Baptist Health deliverable
make report
# Output: reports/validation_report.md
```

---

## Teardown

```bash
make gke-teardown   # Destructive. Deletes cluster, Cloud SQL, Memorystore.
                    # Pass -- --force to skip confirmation prompt.
```

---

## Report

`make report` runs the full test suite and writes `reports/validation_report.md`.
This file is the Baptist Health deliverable — it maps test results to the acceptance
criteria from `doc/Specify.md` Section 16 and provides a timestamped audit trail.

---

## Repository Map

```
doc/Specify.md                  Authoritative specification (source of truth)
doc/Plan.md                     Epic and ticket breakdown
doc/Runbook.md                  Step-by-step operational guide with expected outputs
doc/ADR/                        Four architecture decision records (ADR-001 to ADR-004)
config/contextforge.example.yaml  ContextForge configuration template
scripts/gke_provision.sh        GKE + Cloud SQL + Memorystore provisioning (idempotent)
scripts/gke_deploy.sh           Kubernetes manifest deployment (idempotent)
scripts/gke_teardown.sh         Destructive teardown
scripts/register_proxy.py       POST /v1/proxies — registers GitLab MCP proxy
scripts/create_virtual_server.py  POST /v1/virtual-servers
scripts/generate_report.py      Runs tests and writes reports/validation_report.md
tests/conftest.py               require_full_stack and require_infra_stack fixtures
tests/test_c0_foundation.py     through tests/test_c6_documentation.py
.env.example                    Environment variable template (committed, safe)
.env                            Populated variables (never committed)
```
