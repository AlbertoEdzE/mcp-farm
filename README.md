# MCP Farm

Enterprise MCP gateway for the Baptist Health AI platform, built on IBM ContextForge deployed to Google Kubernetes Engine.

MCP Farm provides a single governed access point through which AI agents discover, authenticate against, and invoke tools registered in the gateway. External vendor MCPs (GitLab, Snowflake) are registered as proxies; tool access for each AI agent role is scoped via virtual servers.

**Current state:** ContextForge is deployed and running on GKE in the `x-ai-engineering` sandbox project, namespace `mcp-farm`. The Admin UI is accessible via Cloud Shell Web Preview (see Access section below).

---

## Prerequisites

**Required tools**

| Tool | Minimum version | Purpose |
|---|---|---|
| Python | 3.11 | Test suite, operational scripts |
| Docker | 24.x | Local stack via Docker Compose |
| make | 3.8 | Task runner |
| gcloud | 460.x | GKE provisioning |
| kubectl | 1.29 | Kubernetes operations |

**Open questions — must be resolved before full production deployment**

| ID | Question | Owner | Status |
|---|---|---|---|
| Q1 | IBM ContextForge image URI | Kashyap | Resolved — `ghcr.io/ibm/mcp-context-forge:latest` (public, Apache 2.0) |
| Q2 | GCP sandbox project ID | Chakri | Resolved — `x-ai-engineering` |
| Q4 | GitLab OAuth client ID and secret | Bala | Pending |
| Q5 | GCP Secret Manager vs Kubernetes Secrets | Chakri | Pending |
| Q6 | GKE node machine type and count | Lakshman | Pending |

---

## Quick Start — Local Environment

```bash
# 1. Clone and install
git clone https://github.com/AlbertoEdzE/mcp-farm.git
cd mcp-farm
cp .env.example .env          # populate required values — see .env.example comments

# 2. Install Python dependencies
make install

# 3. Generate synthetic test data
make generate-data

# 4. Run structural tests (no stack required)
make test CLUSTER=c0,c1,c2,c3,c4,c5,c6

# 5. Start local Docker Compose stack
make local-up
make register-proxy
make create-virtual-server
make test
```

---

## Quick Start — GKE Deployment

Run in this exact order. Each step depends on the previous completing successfully.

```bash
# 1. Provision GKE cluster, Cloud SQL, and Memorystore
make gke-provision
# After: retrieve Cloud SQL private IP and Memorystore host — update .env before proceeding

# 2. Deploy ContextForge to GKE
make gke-deploy

# 3. Change the default admin password (writes new password to .env automatically)
make change-admin-password

# 4. Register MCP proxy and create virtual server
make register-proxy
make create-virtual-server

# 5. Run full test suite and generate Baptist Health validation report
make report
```

---

## Accessing the Admin UI

ContextForge is a single FastAPI application running on port 4444 inside the container. The Kubernetes Service exposes it on ClusterIP port 80.

**Current access method — Cloud Shell Web Preview:**

GCP org policy on `x-ai-engineering` restricts all external Load Balancer types, so no public IP is available. Access is via `kubectl port-forward` tunnelled through Cloud Shell Web Preview.

```bash
# In Cloud Shell (handles pod health check, port-forward, and credential verification)
make demo-start
```

Then: Cloud Shell toolbar → Web Preview → port 8080 → append `/admin` to the URL.

The `make demo-start` command also verifies the admin password in `.env` and prompts to correct it if needed.

**Note:** The `cloudshell.dev` URL is tied to the active Cloud Shell session and requires Google authentication. It is not a public URL. A proper public endpoint requires an org-level GCP policy exemption to allow `EXTERNAL_HTTP_HTTPS` load balancers on `x-ai-engineering`.

---

## Make Targets

| Target | Description |
|---|---|
| `make install` | Install prerequisites and create Python virtual environment |
| `make local-up` | Start Docker Compose stack (ContextForge + PostgreSQL + Redis) |
| `make local-down` | Stop Docker Compose stack and remove volumes |
| `make generate-data` | Generate deterministic synthetic test fixtures (seed 42) |
| `make register-proxy` | Register the GitLab MCP proxy with ContextForge |
| `make create-virtual-server` | Create the test virtual server in ContextForge |
| `make change-admin-password` | Change the admin password via API and update `.env` |
| `make demo-start` | Verify pod health, start port-forward, validate credentials (run in Cloud Shell) |
| `make gke-provision` | Provision GKE cluster, Cloud SQL, and Memorystore |
| `make gke-deploy` | Deploy ContextForge Kubernetes manifests to GKE |
| `make gke-teardown` | Destroy all GKE and managed GCP resources (destructive) |
| `make test` | Run full test suite (filter: `make test CLUSTER=c0,c1`) |
| `make report` | Run tests and write `reports/validation_report.md` |
| `make lint` | Run ruff linter |
| `make typecheck` | Run mypy type checker |
| `make clean` | Remove generated artefacts |

---

## Running Tests

Tests are organised by cluster. Each cluster's tests build on prior ones — run progressively.

```bash
# Structural only (always safe to run, no stack needed)
make test CLUSTER=c0,c1,c2,c3,c4,c5,c6

# With local stack running
make local-up
make test

# Against GKE deployment (requires port-forward active via make demo-start)
TEST_TARGET=gke TEST_GATEWAY_BASE_URL=http://localhost:8080 make test
```

| Cluster | Tests |
|---|---|
| C0 | 18 structural |
| C1 | 13 structural + 6 integration |
| C2 | 8 structural + 4 integration |
| C3 | 34 structural |
| C4 | 14 structural + 4 integration |
| C5 | 17 structural + 4 integration |
| C6 | structural |

---

## Cluster Map

| Cluster | Epic | Description | Status |
|---|---|---|---|
| C0 | E01 | Repository foundation — directory structure, env templates, Makefile | Done |
| C1 | E02 | Local environment — Docker Compose, scripts, synthetic data fixtures | Done |
| C2 | E03 | ContextForge baseline — ADR-001, health paths, UI and Admin API config | Done |
| C3 | E04 | GKE infrastructure — provision/deploy/teardown scripts, ADR-002 | Done |
| C4 | E05 | MCP proxy registration — GitLab proxy, OAuth strategy, ADR-003 | Done |
| C5 | E06 | Virtual server — tool scoping, access boundary, ADR-004 | Done |
| C6 | E07 | Documentation and runbook | Done |

---

## Architecture

```
Baptist Health AI agents
         |
         v
  ContextForge (port 4444 in-container)
  IBM public image: ghcr.io/ibm/mcp-context-forge:latest
         |
  Kubernetes Service (ClusterIP, port 80)
         |
         +---> Cloud SQL (PostgreSQL 15) — configuration and virtual server storage
         +---> Memorystore (Redis 7)     — session cache
         +---> mcp-demo-svc              — in-cluster demo MCP backend (port 9000)
```

**Current access path:**

```
Browser
  | HTTPS
Cloud Shell Web Preview (cloudshell.dev)
  | HTTP proxied
kubectl port-forward localhost:8080 -> contextforge-svc:80
  | in-cluster TCP
ContextForge Pod (GKE node, mcp-farm namespace)
```

**Local development mirrors GKE:**

```
docker-compose.yml
  contextforge  ->  k8s/deployment.yaml
  postgres      ->  Cloud SQL
  redis         ->  Memorystore
```

---

## Architecture Decision Records

| ADR | Decision |
|---|---|
| ADR-001 | GKE over Cloud Run — documents the Cloud Run failure root causes |
| ADR-002 | Cloud SQL and Memorystore over in-cluster StatefulSets |
| ADR-003 | Static OAuth 2.0 client registration for GitLab MCP proxy |
| ADR-004 | Virtual server as the agent access control boundary |

---

## Repository Structure

```
mcp-farm/
  config/                    # Configuration templates
    contextforge.example.yaml
  doc/
    ADR/                     # Architecture Decision Records
    Plan.md                  # Epic and ticket breakdown
    Runbook.md               # Step-by-step operational guide
    Specify.md               # Authoritative specification
    demo_handbook.md         # Step-by-step demo guide for Chakri review
  k8s/                       # Kubernetes manifests
    namespace.yaml
    configmap.yaml
    deployment.yaml
    service.yaml
    ingress.yaml
    backend-config.yaml
    mcp-demo-server.yaml
  scripts/                   # Operational scripts
    gke_provision.sh         # Provision GKE + Cloud SQL + Memorystore
    gke_deploy.sh            # Deploy manifests to GKE
    gke_teardown.sh          # Destroy all GCP resources
    demo_start.sh            # Start port-forward and verify credentials
    register_proxy.py        # Register MCP proxy in ContextForge
    create_virtual_server.py # Create virtual server in ContextForge
    change_admin_password.py # Change admin password via API
    generate_report.py       # Run tests and write validation report
  tests/
    fixtures/                # Deterministic synthetic data (seed 42)
    conftest.py
    test_c0_foundation.py    # through test_c6_documentation.py
  .env.example               # Environment variable template (committed)
  .env                       # Populated values (never committed)
  docker-compose.yml
  Makefile
```

---

## Team

| Name | Role |
|---|---|
| Alberto Hernandez | Engineer — implementation |
| Lakshman | Architect |
| Kashyap | Infrastructure / ContextForge setup |
| Chakri | GCP sandbox provisioning |
| Bala | GitLab OAuth 2.0 |
| Uday | Infrastructure |
